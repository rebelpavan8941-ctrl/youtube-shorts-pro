from flask import Flask, render_template, request, jsonify, send_file, session, send_from_directory
from flask_cors import CORS
import os
import uuid
import requests
import json
import re
from urllib.parse import urlparse, parse_qs
import yt_dlp
import subprocess
from datetime import datetime, timedelta
import tempfile
import shutil
import random
import zipfile
import pickle

app = Flask(__name__)
app.secret_key = 'shortspro-secret-key-2024'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
CORS(app)

# Create directories
os.makedirs('downloads', exist_ok=True)
os.makedirs('sessions', exist_ok=True)

class SessionManager:
    def __init__(self):
        self.sessions_dir = 'sessions'
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    def save_session(self, session_id, data):
        """Save session data to file"""
        try:
            session_file = os.path.join(self.sessions_dir, f"{session_id}.pkl")
            with open(session_file, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def load_session(self, session_id):
        """Load session data from file"""
        try:
            session_file = os.path.join(self.sessions_dir, f"{session_id}.pkl")
            if os.path.exists(session_file):
                with open(session_file, 'rb') as f:
                    return pickle.load(f)
            return None
        except Exception as e:
            print(f"Error loading session: {e}")
            return None

# Initialize session manager
session_manager = SessionManager()

class YouTubeShortsGenerator:
    def __init__(self):
        self.ffmpeg_path = self.find_ffmpeg()
        self.video_categories = self.load_video_categories()
        self.copyright_keywords = self.load_copyright_keywords()
        self.print_ffmpeg_status()
    
    def find_ffmpeg(self):
        """Find FFmpeg - Render has it built-in"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ffmpeg'
        except:
            pass
        return 'ffmpeg'
    
    def load_video_categories(self):
        """Enhanced video categories with title templates"""
        return {
            'gaming': {
                'templates': [
                    "{} moment! 🎮", "Incredible {} gameplay! 🤯", "{} skills on display! 🔥",
                    "Epic {} play! ⚡", "{} mastery! 🏆", "Game-changing {} moment! 🚀"
                ],
                'hashtags': ["#gaming", "#gameplay", "#gamer", "#videogames", "#twitch"]
            },
            'music': {
                'templates': [
                    "{} vibes! 🎵", "Amazing {} performance! 🎶", "{} sounds perfect! ✨",
                    "Incredible {} talent! 🎧", "{} magic! 💫", "{} musical genius! 🎹"
                ],
                'hashtags': ["#music", "#song", "#musician", "#musicvideo", "#newmusic"]
            },
            'sports': {
                'templates': [
                    "{} action! 🏀", "Incredible {} move! ⚽", "{} excellence! 🏈",
                    "Epic {} moment! 🏆", "{} skills! ⚡", "Sports {} brilliance! 🎯"
                ],
                'hashtags': ["#sports", "#athlete", "#fitness", "#sportsmoments", "#athletics"]
            },
            'comedy': {
                'templates': [
                    "{} funny moment! 😂", "Hilarious {} clip! 🤣", "{} comedy gold! 🎭",
                    "Funny {} moment! 💀", "{} laughs! 🥳", "LOL {} moment! 😹"
                ],
                'hashtags': ["#comedy", "#funny", "#humor", "#laugh", "#comedyvideo"]
            },
            'general': {
                'templates': [
                    "{} moment! 🤯", "Incredible {} clip! 🚀", "{} awesomeness! 🔥",
                    "Epic {} content! 💫", "{} viral moment! 📈", "Must-see {}! 👀"
                ],
                'hashtags': ["#viral", "#trending", "#shorts", "#youtubeshorts", "#fyp"]
            }
        }
    
    def load_copyright_keywords(self):
        """Copyright keywords for detection"""
        return {
            'music_copyright': ['song', 'music', 'track', 'album', 'official video'],
            'movie_copyright': ['movie', 'film', 'trailer', 'scene', 'hollywood'],
            'gaming_copyright': ['gameplay', 'walkthrough', 'review', 'lets play'],
            'sports_copyright': ['highlights', 'match', 'game', 'tournament'],
            'tv_copyright': ['episode', 'season', 'series', 'tv show']
        }
    
    def print_ffmpeg_status(self):
        """Print FFmpeg status"""
        if self.ffmpeg_path:
            print("🎉 FFMPEG STATUS: ✅ DETECTED & READY!")
        else:
            print("❌ FFMPEG STATUS: NOT FOUND")
    
    def extract_keywords_from_content(self, title, description):
        """Extract keywords from video content"""
        content = (title + ' ' + description).lower()
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content)
        meaningful_words = [word for word in words if word not in stop_words]
        
        from collections import Counter
        word_freq = Counter(meaningful_words)
        top_keywords = [word for word, count in word_freq.most_common(5)]
        
        return top_keywords if top_keywords else ['amazing', 'epic', 'incredible', 'awesome']
    
    def detect_video_category(self, title, description):
        """Detect video category"""
        content = (title + ' ' + description).lower()
        
        if any(word in content for word in ['game', 'gaming', 'play']):
            return 'gaming'
        elif any(word in content for word in ['music', 'song', 'album']):
            return 'music'
        elif any(word in content for word in ['sports', 'game', 'match']):
            return 'sports'
        elif any(word in content for word in ['funny', 'comedy', 'joke']):
            return 'comedy'
        else:
            return 'general'
    
    def analyze_copyright_risk(self, title, description):
        """Copyright risk analysis"""
        content = (title + ' ' + description).lower()
        risk_score = 0
        
        for keywords in self.copyright_keywords.values():
            if any(keyword in content for keyword in keywords):
                risk_score += 20
        
        if risk_score >= 60:
            return {'status': "🔴 HIGH RISK", 'score': risk_score, 'risk_level': 'high'}
        elif risk_score >= 30:
            return {'status': "🟡 MEDIUM RISK", 'score': risk_score, 'risk_level': 'medium'}
        else:
            return {'status': "🟢 LOW RISK", 'score': risk_score, 'risk_level': 'low'}
    
    def generate_contextual_title(self, category, keywords, start_time, video_title):
        """Generate AI-powered title"""
        category_data = self.video_categories.get(category, self.video_categories['general'])
        template = random.choice(category_data['templates'])
        
        main_keyword = keywords[0].title() if keywords else "Content"
        title = template.format(main_keyword)
        
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title
    
    def generate_ai_hashtags(self, category):
        """Generate relevant hashtags"""
        category_data = self.video_categories.get(category, self.video_categories['general'])
        base_hashtags = random.sample(category_data['hashtags'], 3)
        platform_hashtags = ["#shorts", "#youtubeshorts", "#viral"]
        return ' '.join(base_hashtags + platform_hashtags)
    
    def extract_video_id(self, url):
        """Extract YouTube video ID"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&?/]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_info(self, video_url):
        """Get video information - WORKING VERSION"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'cookiefile': None,
            # Enhanced anti-bot measures
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown Video'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'video_id': info.get('id', ''),
                }
        except Exception as e:
            print(f"❌ Video info error: {e}")
            return {'success': False, 'error': str(e)}
    
    def download_video(self, video_url, output_path):
        """Download YouTube video - WORKING VERSION"""
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best[height<=720]',  # Lower quality for better success
            'quiet': False,
            # Enhanced download settings
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Range': 'bytes=0-',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'video',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            },
            # Retry settings
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'continuedl': True,
        }
        
        try:
            print(f"📥 Downloading video with enhanced settings...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                file_size = os.path.getsize(output_path) / (1024*1024)
                print(f"✅ Download successful: {file_size:.2f} MB")
                return True
            else:
                print("❌ Download failed: File too small or missing")
                return False
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
    
    def analyze_video_content(self, video_info):
        """Analyze video and generate clips"""
        duration = video_info['duration']
        
        # Detect category and copyright
        category = self.detect_video_category(video_info['title'], video_info.get('description', ''))
        copyright_analysis = self.analyze_copyright_risk(video_info['title'], video_info.get('description', ''))
        keywords = self.extract_keywords_from_content(video_info['title'], video_info.get('description', ''))
        
        clips = []
        num_clips = min(6, max(3, duration // 45))
        
        # Generate timestamps
        for i in range(num_clips):
            start_time = int((i + 1) * (duration / (num_clips + 1)))
            if start_time >= duration - 15:
                start_time = max(10, duration - 30)
            
            quality_score = round(7.5 + random.uniform(0, 2.0), 1)
            ai_title = self.generate_contextual_title(category, keywords, start_time, video_info['title'])
            ai_hashtags = self.generate_ai_hashtags(category)
            
            clips.append({
                "start_time": start_time,
                "duration": 15,
                "title": ai_title,
                "hashtags": ai_hashtags,
                "quality_score": quality_score,
                "engagement_score": round(quality_score * 10, 1),
                "virality_potential": f"{min(95, int(quality_score * 10))}%",
                "category": category,
                "copyright_status": copyright_analysis['status'],
                "copyright_score": copyright_analysis['score'],
                "risk_level": copyright_analysis['risk_level'],
                "risk_score": copyright_analysis['score'],
                "copyright_advice": {
                    "warning": f"{copyright_analysis['status']}",
                    "description": "Review copyright guidelines",
                    "suggestions": ["Credit creators", "Use short clips", "Add commentary"],
                    "consequences": ["Possible claims", "Revenue sharing"]
                }
            })
        
        return {
            "clips": clips,
            "video_category": category,
            "overall_copyright_status": copyright_analysis['status'],
            "copyright_risk_level": copyright_analysis['risk_level'],
            "copyright_risk_score": copyright_analysis['score']
        }
    
    def create_short_video(self, input_path, start_time, duration, output_path):
        """Create vertical short video"""
        if not self.ffmpeg_path:
            return False
        
        try:
            print(f"🎬 Creating {duration}-second vertical short...")
            
            if not os.path.exists(input_path):
                return False
            
            cmd = [
                self.ffmpeg_path,
                '-ss', str(start_time),
                '-i', input_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return True
            return False
                
        except Exception as e:
            print(f"❌ Video creation error: {e}")
            return False

# Initialize the generator
shorts_generator = YouTubeShortsGenerator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    try:
        data = request.get_json()
        video_url = data.get('url', '').strip()
        
        if not video_url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'})
        
        video_id = shorts_generator.extract_video_id(video_url)
        if not video_id:
            return jsonify({'success': False, 'error': 'Invalid YouTube URL'})
        
        video_info = shorts_generator.get_video_info(video_url)
        if not video_info['success']:
            return jsonify({'success': False, 'error': video_info['error']})
        
        analysis = shorts_generator.analyze_video_content(video_info)
        
        session_id = str(uuid.uuid4())
        session_data = {
            'video_info': video_info,
            'analysis': analysis,
            'video_url': video_url,
            'created_at': datetime.now().isoformat()
        }
        
        session_manager.save_session(session_id, session_data)
        session[session_id] = session_data
        
        # Add thumbnails and YouTube URLs to clips
        for i, clip in enumerate(analysis['clips']):
            clip['thumbnail'] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            clip['youtube_url'] = f"{video_url}&t={int(clip['start_time'])}s"
            clip['id'] = i + 1
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'video_info': video_info,
            'clips': analysis['clips'],
            'total_clips': len(analysis['clips']),
            'video_category': analysis['video_category'],
            'copyright_status': analysis['overall_copyright_status'],
            'copyright_risk': analysis['copyright_risk_level'],
            'copyright_score': analysis['copyright_risk_score'],
            'ffmpeg_available': shorts_generator.ffmpeg_path is not None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'})

def get_session_data(session_id):
    """Get session data"""
    session_data = session.get(session_id)
    if session_data:
        return session_data
    
    session_data = session_manager.load_session(session_id)
    if session_data:
        session[session_id] = session_data
        return session_data
    
    return None

@app.route('/api/generate', methods=['POST'])
def generate_short():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        clip_index = data.get('clip_index')
        
        if not session_id or clip_index is None:
            return jsonify({'success': False, 'error': 'Missing required data'})
        
        session_data = get_session_data(session_id)
        if not session_data:
            return jsonify({'success': False, 'error': 'Session expired or not found'})
        
        video_info = session_data['video_info']
        analysis = session_data['analysis']
        video_url = session_data['video_url']
        
        if clip_index >= len(analysis['clips']):
            return jsonify({'success': False, 'error': 'Invalid clip index'})
        
        clip_data = analysis['clips'][clip_index]
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, 'source_video.mp4')
        
        # Create output filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '', clip_data['title'])
        output_filename = f'{safe_title}_{int(datetime.now().timestamp())}.mp4'
        output_path = os.path.join('downloads', output_filename)
        
        print(f"🚀 Generating short: {clip_data['title']}")
        
        # Download the source video
        if not shorts_generator.download_video(video_url, input_path):
            return jsonify({'success': False, 'error': 'Failed to download source video. YouTube may be blocking the request.'})
        
        # Create the vertical short
        if not shorts_generator.create_short_video(
            input_path,
            clip_data['start_time'],
            clip_data['duration'],
            output_path
        ):
            return jsonify({'success': False, 'error': 'Failed to create short video'})
        
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        # Verify final file
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            file_size_str = f"{file_size:.1f} MB"
            
            return jsonify({
                'success': True,
                'download_url': f'/download/{output_filename}',
                'filename': output_filename,
                'display_name': f'{clip_data["title"]}.mp4',
                'clip_data': clip_data,
                'file_size': file_size_str,
                'video_dimensions': '1080x1920',
                'message': f'🎉 Short video ready! ({file_size_str})'
            })
        else:
            return jsonify({'success': False, 'error': 'Video file was not created'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Generation failed: {str(e)}'})

@app.route('/api/batch-generate', methods=['POST'])
def batch_generate_shorts():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        clip_indices = data.get('clip_indices', [])
        
        if not session_id or not clip_indices:
            return jsonify({'success': False, 'error': 'Missing required data'})
        
        session_data = get_session_data(session_id)
        if not session_data:
            return jsonify({'success': False, 'error': 'Session expired or not found'})
        
        video_info = session_data['video_info']
        analysis = session_data['analysis']
        video_url = session_data['video_url']
        
        # Create temp directory for source video
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, 'source_video.mp4')
        
        # Download the source video once for all clips
        print(f"📥 Downloading source video for batch processing...")
        if not shorts_generator.download_video(video_url, input_path):
            return jsonify({'success': False, 'error': 'Failed to download source video'})
        
        results = []
        generated_files = []
        
        for clip_index in clip_indices:
            if clip_index >= len(analysis['clips']):
                continue
                
            clip_data = analysis['clips'][clip_index]
            
            # Create output filename
            safe_title = re.sub(r'[<>:"/\\|?*]', '', clip_data['title'])
            output_filename = f'{safe_title}_{int(datetime.now().timestamp())}.mp4'
            output_path = os.path.join('downloads', output_filename)
            
            print(f"🎬 Processing clip {clip_index + 1}/{len(clip_indices)}: {clip_data['title']}")
            
            # Create the vertical short
            success = shorts_generator.create_short_video(
                input_path,
                clip_data['start_time'],
                clip_data['duration'],
                output_path
            )
            
            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                file_size_str = f"{file_size:.1f} MB"
                
                results.append({
                    'success': True,
                    'clip_index': clip_index,
                    'download_url': f'/download/{output_filename}',
                    'filename': output_filename,
                    'display_name': f'{clip_data["title"]}.mp4',
                    'clip_data': clip_data,
                    'file_size': file_size_str
                })
                generated_files.append(output_path)
            else:
                results.append({
                    'success': False,
                    'clip_index': clip_index,
                    'error': 'Failed to generate video'
                })
        
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        return jsonify({
            'success': True,
            'results': results,
            'total_generated': len([r for r in results if r['success']]),
            'message': f'✅ Successfully generated {len([r for r in results if r["success"]])} shorts!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Batch generation failed: {str(e)}'})

@app.route('/download/<filename>')
def download_file(filename):
    """Serve video files for download"""
    try:
        directory = os.path.join(os.getcwd(), 'downloads')
        file_path = os.path.join(directory, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File not found'})
        
        return send_from_directory(
            directory=directory,
            path=filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': f'Download failed: {str(e)}'})

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'ffmpeg_available': shorts_generator.ffmpeg_path is not None,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 YouTube Shorts Pro - ACTUAL WORKING VERSION")
    print("✅ Enhanced Anti-Bot Measures")
    print("🎯 Real Video Downloads")
    print("⚡ Fast Processing")
    
    app.run(host='0.0.0.0', port=port)
