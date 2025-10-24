class ShortsProAI {
    constructor() {
        this.currentSession = null;
        this.selectedClips = new Set();
        this.currentAIVideo = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.animateStats();
        this.setupAIVideoGenerator();
        console.log('🚀 ShortsPro AI initialized with Video Generator');
    }

    bindEvents() {
        // Analyze button
        document.getElementById('analyze-btn').addEventListener('click', () => this.analyzeVideo());
        
        // Example URLs
        document.querySelectorAll('.example-url').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const url = e.target.getAttribute('data-url');
                if (url) {
                    document.getElementById('video-url').value = url;
                    this.showNotification('Example URL loaded. Click "Analyze Video" to continue.', 'info');
                }
            });
        });

        // Enter key in URL input
        document.getElementById('video-url').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.analyzeVideo();
        });

        // Batch actions
        document.getElementById('select-all-btn').addEventListener('click', () => this.toggleSelectAll());
        document.getElementById('generate-batch-btn').addEventListener('click', () => this.generateBatch());
    }

    setupAIVideoGenerator() {
        // Setup tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target));
        });

        // Setup AI video generation
        document.getElementById('generate-ai-video-btn').addEventListener('click', () => this.generateAIVideo());
        
        // Setup prompt examples
        document.querySelectorAll('.example-url[data-prompt]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const prompt = e.target.getAttribute('data-prompt');
                document.getElementById('ai-prompt').value = prompt;
                this.showNotification('Example prompt loaded! Click "Generate AI Video" to continue.', 'info');
            });
        });

        // Enter key in AI prompt input
        document.getElementById('ai-prompt').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.generateAIVideo();
        });
    }

    switchTab(clickedBtn) {
        // Remove active class from all tabs and contents
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        // Add active class to clicked tab
        clickedBtn.classList.add('active');
        
        // Show corresponding content
        const tabName = clickedBtn.getAttribute('data-tab');
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Update analysis status message
        const statusElement = document.getElementById('analysis-status');
        if (tabName === 'ai-video') {
            statusElement.querySelector('h3').textContent = 'AI Video Generator Ready';
            statusElement.querySelector('p').textContent = 'Describe your funny video idea and let AI create it!';
        } else {
            statusElement.querySelector('h3').textContent = 'AI Analysis Ready';
            statusElement.querySelector('p').textContent = 'Paste a YouTube URL above to start analysis';
        }
    }

    animateStats() {
        const stats = {
            'stats-processed': 1247,
            'stats-generated': 8956,
            'stats-success': 98
        };

        Object.keys(stats).forEach(statId => {
            const element = document.getElementById(statId);
            if (element) {
                this.animateCounter(element, stats[statId], statId === 'stats-success' ? '%' : '');
            }
        });
    }

    animateCounter(element, target, suffix = '') {
        let current = 0;
        const increment = target / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current).toLocaleString() + suffix;
        }, 30);
    }

    async analyzeVideo() {
        const urlInput = document.getElementById('video-url');
        const url = urlInput.value.trim();
        
        if (!url) {
            this.showNotification('Please enter a YouTube URL', 'error');
            return;
        }
        if (!this.isValidYouTubeUrl(url)) {
            this.showNotification('Please enter a valid YouTube URL', 'error');
            return;
        }

        // Show loading modal
        this.showLoadingModal('Analyzing YouTube Video', 'AI is processing your video to find the best moments...');

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();
            if (data.success) {
                this.currentSession = data.session_id;
                this.displayResults(data);
                this.showNotification('🎉 Video analysis complete! Found ' + data.total_clips + ' engaging moments.', 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification('Analysis failed: ' + error.message, 'error');
            console.error('Analysis error:', error);
        } finally {
            this.hideLoadingModal();
        }
    }

    isValidYouTubeUrl(url) {
        const patterns = [
            /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)/,
            /youtube\.com\/watch\?.*v=([^&]+)/,
            /youtu\.be\/([^&]+)/
        ];
        return patterns.some(pattern => pattern.test(url));
    }

    displayResults(data) {
        // Update analysis status
        const analysisStatus = document.getElementById('analysis-status');
        analysisStatus.innerHTML = `
            <div class="status-content">
                <i class="fas fa-check-circle" style="color: var(--success);"></i>
                <div class="status-text">
                    <h3>Analysis Complete</h3>
                    <p>Found ${data.total_clips} engaging moments in your video</p>
                    <div class="copyright-overview ${data.copyright_risk === 'high' ? 'copyright-high' : data.copyright_risk === 'medium' ? 'copyright-medium' : 'copyright-low'}">
                        <i class="fas fa-copyright"></i>
                        Overall Copyright Risk: ${data.copyright_status} (${data.copyright_score}/100)
                    </div>
                </div>
            </div>
        `;

        // Show video summary
        const videoSummary = document.getElementById('video-summary');
        videoSummary.innerHTML = `
            <div class="video-info">
                <div class="video-thumbnail">
                    <img src="${data.video_info.thumbnail}" alt="${data.video_info.title}">
                </div>
                <div class="video-details">
                    <h3>${data.video_info.title}</h3>
                    <div class="video-meta">
                        <span><i class="fas fa-clock"></i> ${this.formatDuration(data.video_info.duration)}</span>
                        <span><i class="fas fa-eye"></i> ${this.formatNumber(data.video_info.view_count)} views</span>
                        <span><i class="fas fa-user"></i> ${data.video_info.uploader}</span>
                        <span><i class="fas fa-tag"></i> ${data.video_category}</span>
                    </div>
                </div>
            </div>
        `;

        // Display clips
        this.displayClips(data.clips);

        // Show results section
        document.getElementById('results-section').style.display = 'block';
        document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
    }

    displayClips(clips) {
        const clipsGrid = document.getElementById('clips-grid');
        
        clipsGrid.innerHTML = clips.map((clip, index) => `
            <div class="clip-card" data-clip-index="${index}">
                <div class="clip-header">
                    <img src="${clip.thumbnail}" alt="${clip.title}" class="clip-thumbnail">
                    <div class="clip-overlay">
                        <span class="duration-badge">${this.formatTime(clip.start_time)}</span>
                        <span class="quality-badge ${clip.quality_score >= 8.5 ? 'excellent' : clip.quality_score >= 7 ? 'good' : 'average'}">
                            ${clip.quality_score >= 8.5 ? 'EXCELLENT' : clip.quality_score >= 7 ? 'GOOD' : 'AVERAGE'}
                        </span>
                    </div>
                    <div class="clip-engagement">
                        <span class="engagement-score">
                            <i class="fas fa-chart-line"></i>
                            ${clip.engagement_score}% Engagement
                        </span>
                        <span class="virality-score">
                            <i class="fas fa-share-alt"></i>
                            ${clip.virality_potential} Viral
                        </span>
                    </div>
                </div>
                <div class="clip-content">
                    <h3 class="clip-title">${clip.title}</h3>
                    
                    <div class="clip-hashtags">
                        ${clip.hashtags.split(' ').map(tag => 
                            `<span class="hashtag">${tag}</span>`
                        ).join('')}
                    </div>
                    
                    <!-- Copyright Status Display -->
                    <div class="copyright-info">
                        <div class="copyright-status ${clip.risk_level === 'high' ? 'copyright-high' : clip.risk_level === 'medium' ? 'copyright-medium' : 'copyright-low'}">
                            <i class="fas fa-copyright"></i>
                            ${clip.copyright_status}
                            <span class="risk-score">${clip.risk_score}/100</span>
                        </div>
                        
                        <div class="copyright-details">
                            <div class="copyright-warning">
                                <strong>${clip.copyright_advice.warning}</strong>
                                <p>${clip.copyright_advice.description}</p>
                            </div>
                            
                            <div class="advice-section">
                                <h4><i class="fas fa-lightbulb"></i> Suggestions:</h4>
                                <ul>
                                    ${clip.copyright_advice.suggestions.map(suggestion =>
                                        `<li>${suggestion}</li>`
                                    ).join('')}
                                </ul>
                            </div>
                            
                            <div class="consequences-section">
                                <h4><i class="fas fa-exclamation-triangle"></i> Possible Consequences:</h4>
                                <ul>
                                    ${clip.copyright_advice.consequences.map(consequence =>
                                        `<li>${consequence}</li>`
                                    ).join('')}
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <div class="clip-meta">
                        <span><i class="fas fa-clock"></i> ${clip.duration}s duration</span>
                        <span><i class="fas fa-star"></i> Score: ${clip.quality_score}/10</span>
                        <span><i class="fas fa-brain"></i> AI Selected</span>
                    </div>
                    
                    <div class="clip-actions">
                        <button class="btn-generate" onclick="shortsPro.generateSingleClip(${index})">
                            <i class="fas fa-download"></i>
                            Generate This Short
                        </button>
                        <label class="clip-checkbox">
                            <input type="checkbox" onchange="shortsPro.toggleClipSelection(${index})">
                            <span class="checkmark"></span>
                            Select for Batch
                        </label>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async generateSingleClip(clipIndex) {
        if (!this.currentSession) {
            this.showNotification('Please analyze a video first', 'error');
            return;
        }

        this.showLoadingModal('Generating Short Video', 'Creating optimized vertical short...');

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.currentSession,
                    clip_index: clipIndex
                })
            });

            const data = await response.json();
            if (data.success) {
                this.downloadFile(data.download_url, `short-${Date.now()}.mp4`);
                
                // Show appropriate notification based on copyright risk
                const clipData = data.clip_data;
                if (clipData.risk_level === 'high') {
                    this.showNotification(
                        `⚠️ HIGH COPYRIGHT RISK: ${clipData.copyright_advice.warning}. Check the analysis for details.`,
                        'error',
                        8000
                    );
                } else if (clipData.risk_level === 'medium') {
                    this.showNotification(
                        `⚠️ MEDIUM COPYRIGHT RISK: ${clipData.copyright_advice.description}`,
                        'warning',
                        6000
                    );
                } else {
                    this.showNotification('✅ Short video generated successfully! Download started.', 'success');
                }
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification('Generation failed: ' + error.message, 'error');
            console.error('Generation error:', error);
        } finally {
            this.hideLoadingModal();
        }
    }

    async generateAIVideo() {
        const promptInput = document.getElementById('ai-prompt');
        const prompt = promptInput.value.trim();
        
        if (!prompt) {
            this.showNotification('Please enter a video description', 'error');
            return;
        }

        if (prompt.length < 5) {
            this.showNotification('Please provide a more detailed description (at least 5 characters)', 'error');
            return;
        }

        // Show loading modal
        this.showLoadingModal('Creating AI Video', 'AI is generating your custom video... This may take a moment.');

        try {
            const response = await fetch('/api/generate-ai-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: prompt })
            });

            const data = await response.json();
            
            if (data.success) {
                this.currentAIVideo = data;
                this.displayAIVideoResult(data);
                this.showNotification('🎉 AI video generated successfully!', 'success');
                
                // Scroll to results
                document.getElementById('ai-video-results-section').style.display = 'block';
                document.getElementById('ai-video-results-section').scrollIntoView({ behavior: 'smooth' });
            } else {
                throw new Error(data.error || 'Failed to generate AI video');
            }
        } catch (error) {
            this.showNotification('AI video generation failed: ' + error.message, 'error');
            console.error('AI Video generation error:', error);
        } finally {
            this.hideLoadingModal();
        }
    }

    displayAIVideoResult(data) {
        const resultContainer = document.getElementById('ai-video-result');
        
        resultContainer.innerHTML = `
            <div class="ai-video-container">
                <video controls class="ai-generated-video">
                    <source src="${data.video_url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
            <div class="ai-video-info">
                <h3>"${data.prompt}"</h3>
                <p>AI-generated video ready for download</p>
            </div>
            <div class="ai-video-actions">
                <button class="btn-ai-download" onclick="shortsPro.downloadAIVideo()">
                    <i class="fas fa-download"></i>
                    Download Video
                </button>
                <button class="btn-generate-another" onclick="shortsPro.generateAnotherAIVideo()">
                    <i class="fas fa-sync"></i>
                    Generate Another
                </button>
            </div>
        `;

        // Auto-play the video
        const videoElement = resultContainer.querySelector('video');
        videoElement.play().catch(e => console.log('Auto-play prevented:', e));
    }

    downloadAIVideo() {
        if (!this.currentAIVideo) {
            this.showNotification('No AI video available to download', 'error');
            return;
        }

        const link = document.createElement('a');
        link.href = this.currentAIVideo.video_url;
        link.download = `ai-video-${Date.now()}.mp4`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showNotification('📥 AI video download started!', 'success');
    }

    generateAnotherAIVideo() {
        // Clear current results and focus on prompt input
        document.getElementById('ai-prompt').value = '';
        document.getElementById('ai-prompt').focus();
        document.getElementById('ai-video-results-section').style.display = 'none';
        
        this.showNotification('Ready to create another AI video! Enter your idea.', 'info');
    }

    toggleClipSelection(clipIndex) {
        if (this.selectedClips.has(clipIndex)) {
            this.selectedClips.delete(clipIndex);
        } else {
            this.selectedClips.add(clipIndex);
        }

        this.updateBatchButton();
    }

    toggleSelectAll() {
        const checkboxes = document.querySelectorAll('.clip-checkbox input[type="checkbox"]');
        const allSelected = this.selectedClips.size === checkboxes.length;
        
        checkboxes.forEach((checkbox, index) => {
            checkbox.checked = !allSelected;
            if (!allSelected) {
                this.selectedClips.add(index);
            } else {
                this.selectedClips.delete(index);
            }
        });

        const selectAllBtn = document.getElementById('select-all-btn');
        selectAllBtn.innerHTML = allSelected ?
            '<i class="fas fa-check-double"></i> Select All Clips' :
            '<i class="fas fa-times"></i> Deselect All';

        this.updateBatchButton();
    }

    updateBatchButton() {
        const generateBtn = document.getElementById('generate-batch-btn');
        const selectedCount = document.getElementById('selected-count');
        
        generateBtn.disabled = this.selectedClips.size === 0;
        selectedCount.textContent = this.selectedClips.size;
    }

    async generateBatch() {
        if (!this.currentSession || this.selectedClips.size === 0) {
            this.showNotification('Please select at least one clip to generate', 'error');
            return;
        }

        // Check for high-risk clips in selection
        const highRiskClips = Array.from(this.selectedClips).filter(index => {
            const clipCard = document.querySelector(`[data-clip-index="${index}"]`);
            return clipCard && clipCard.querySelector('.copyright-high');
        });

        if (highRiskClips.length > 0) {
            const proceed = confirm(
                `⚠️ You have selected ${highRiskClips.length} clip(s) with HIGH copyright risk.\n\n` +
                `These may receive copyright claims and have limited distribution.\n\n` +
                `Are you sure you want to proceed?`
            );
            
            if (!proceed) {
                return;
            }
        }

        this.showLoadingModal('Generating Multiple Shorts', `Creating ${this.selectedClips.size} optimized short videos...`);

        try {
            // Note: You'll need to implement the batch-generate endpoint in your app.py
            const response = await fetch('/api/batch-generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.currentSession,
                    clip_indices: Array.from(this.selectedClips)
                })
            });

            const data = await response.json();
            if (data.success) {
                // Download all successful generations
                data.results.forEach(result => {
                    if (result.success) {
                        this.downloadFile(result.download_url, `short-${result.clip_index + 1}-${Date.now()}.mp4`);
                    }
                });

                const successCount = data.results.filter(r => r.success).length;
                
                // Show appropriate notification based on risk levels
                const highRiskCount = data.results.filter(r => r.success && r.clip_data.risk_level === 'high').length;
                const mediumRiskCount = data.results.filter(r => r.success && r.clip_data.risk_level === 'medium').length;
                
                let notificationMessage = `✅ Successfully generated ${successCount} short videos!`;
                let notificationType = 'success';
                
                if (highRiskCount > 0) {
                    notificationMessage += `\n⚠️ ${highRiskCount} have HIGH copyright risk.`;
                    notificationType = 'warning';
                } else if (mediumRiskCount > 0) {
                    notificationMessage += `\n⚠️ ${mediumRiskCount} have medium copyright risk.`;
                }
                
                this.showNotification(notificationMessage, notificationType, 6000);
                // Clear selection
                this.selectedClips.clear();
                this.updateBatchButton();
                document.querySelectorAll('.clip-checkbox input[type="checkbox"]').forEach(cb => cb.checked = false);
                
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification('Batch generation failed: ' + error.message, 'error');
            console.error('Batch generation error:', error);
        } finally {
            this.hideLoadingModal();
        }
    }

    downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    showLoadingModal(title, message) {
        const modal = document.getElementById('loading-modal');
        const progressFill = document.getElementById('progress-fill');
        
        document.getElementById('loading-title').textContent = title;
        document.getElementById('loading-message').textContent = message;
        progressFill.style.width = '30%';
        
        modal.style.display = 'flex';
        
        // Animate progress bar
        let progress = 30;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress >= 90) {
                progress = 90;
                clearInterval(progressInterval);
            }
            progressFill.style.width = progress + '%';
        }, 500);
        
        this.progressInterval = progressInterval;
    }

    hideLoadingModal() {
        const modal = document.getElementById('loading-modal');
        const progressFill = document.getElementById('progress-fill');
        
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        progressFill.style.width = '100%';
        
        setTimeout(() => {
            modal.style.display = 'none';
            progressFill.style.width = '0%';
        }, 500);
    }

    showNotification(message, type = 'info', duration = 5000) {
        // Remove existing notifications
        document.querySelectorAll('.notification').forEach(notif => notif.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideInRight 0.3s ease reverse';
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    // New method to get copyright risk summary
    getCopyrightRiskSummary(clips) {
        const riskCounts = {
            high: 0,
            medium: 0,
            low: 0
        };
        
        clips.forEach(clip => {
            riskCounts[clip.risk_level]++;
        });
        
        return riskCounts;
    }
}

// Initialize the application
let shortsPro;
document.addEventListener('DOMContentLoaded', () => {
    shortsPro = new ShortsProAI();
});

// Make functions globally available
window.shortsPro = shortsPro;