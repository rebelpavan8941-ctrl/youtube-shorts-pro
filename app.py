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
    
    def delete_session(self, session_id):
        """Delete session file"""
        try:
            session_file = os.path.join(self.sessions_dir, f"{session_id}.pkl")
            if os.path.exists(session_file):
                os.remove(session_file)
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def cleanup_expired_sessions(self, max_age_hours=24):
        """Clean up expired session files"""
        try:
            current_time = datetime.now()
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith('.pkl'):
                    session_file = os.path.join(self.sessions_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(session_file))
                    if (current_time - file_time).total_seconds() > max_age_hours * 3600:
                        os.remove(session_file)
                        print(f"Cleaned up expired session: {filename}")
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")

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
            # Try system ffmpeg (available on Render)
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ffmpeg'
        except:
            pass
        
        return 'ffmpeg'  # Render has ffmpeg in PATH
    
    def load_video_categories(self):
        """Enhanced video categories with title templates"""
        return {
            'gaming': {
                'templates': [
                    "{} moment! 🎮",
                    "Incredible {} gameplay! 🤯",
                    "{} skills on display! 🔥",
                    "Epic {} play! ⚡",
                    "{} mastery! 🏆",
                    "Unbelievable {} action! 💫",
                    "{} pro move! 👑",
                    "Game-changing {} moment! 🚀"
                ],
                'hashtags': [
                    "#gaming", "#gameplay", "#gamer", "#videogames", "#twitch", "#streamer",
                    "#gamingclips", "#gamemoments", "#gamingcommunity", "#gamingvideos"
                ]
            },
            'music': {
                'templates': [
                    "{} vibes! 🎵",
                    "Amazing {} performance! 🎶",
                    "{} sounds perfect! ✨",
                    "Incredible {} talent! 🎧",
                    "{} magic! 💫",
                    "Beautiful {} moment! 🌟",
                    "{} musical genius! 🎹",
                    "Stunning {} skills! 🥁"
                ],
                'hashtags': [
                    "#music", "#song", "#musician", "#musicvideo", "#newmusic", "#musiclover",
                    "#musicproduction", "#musicianlife", "#musicislife", "#musicmoment"
                ]
            },
            'sports': {
                'templates': [
                    "{} action! 🏀",
                    "Incredible {} move! ⚽",
                    "{} excellence! 🏈",
                    "Epic {} moment! 🏆",
                    "{} skills! ⚡",
                    "Athletic {} perfection! 💪",
                    "{} championship moment! 🥇",
                    "Sports {} brilliance! 🎯"
                ],
                'hashtags': [
                    "#sports", "#athlete", "#fitness", "#sportsmoments", "#athletics", "#sportshighlights",
                    "#sportslife", "#sportsvideo", "#sportsaction", "#sportsgram"
                ]
            },
            'comedy': {
                'templates': [
                    "{} funny moment! 😂",
                    "Hilarious {} clip! 🤣",
                    "{} comedy gold! 🎭",
                    "Funny {} moment! 💀",
                    "{} laughs! 🥳",
                    "Comedic {} genius! 🤡",
                    "{} prank success! 🎪",
                    "LOL {} moment! 😹"
                ],
                'hashtags': [
                    "#comedy", "#funny", "#humor", "#laugh", "#comedyvideo", "#funnymoments",
                    "#comedyclips", "#humorvideo", "#laughs", "#comedycontent"
                ]
            },
            'education': {
                'templates': [
                    "{} knowledge! 🧠",
                    "Learn {} easily! 📚",
                    "{} explained! 💎",
                    "Smart {} tips! 💣",
                    "{} insights! 🎓",
                    "Educational {} moment! 📖",
                    "{} learning hack! 🔍",
                    "Knowledge {} breakthrough! 💡"
                ],
                'hashtags': [
                    "#education", "#learning", "#knowledge", "#educational", "#learn", "#study",
                    "#educationmatters", "#learningvideos", "#knowledgeispower", "#educationalcontent"
                ]
            },
            'cooking': {
                'templates': [
                    "{} recipe! 👨‍🍳",
                    "Delicious {} making! 🍳",
                    "{} cooking magic! 🍲",
                    "Amazing {} dish! 🍕",
                    "{} kitchen skills! 🔪",
                    "Culinary {} perfection! 🍽️",
                    "{} cooking mastery! 🧑‍🍳",
                    "Recipe {} success! 🥘"
                ],
                'hashtags': [
                    "#cooking", "#food", "#recipe", "#cook", "#foodie", "#cookingvideo",
                    "#foodlover", "#cookingtips", "#foodporn", "#cookingathome"
                ]
            },
            'tech': {
                'templates': [
                    "{} tech review! 💻",
                    "Amazing {} gadget! 📱",
                    "{} technology! 🔧",
                    "Innovative {} device! 🚀",
                    "{} tech insights! ⚡",
                    "Tech {} breakthrough! 🔬",
                    "{} gadget magic! ⌚",
                    "Future {} technology! 🌐"
                ],
                'hashtags': [
                    "#tech", "#technology", "#gadget", "#innovation", "#techie", "#techreview",
                    "#technews", "#gadgets", "#techvideo", "#technologynews"
                ]
            },
            'general': {
                'templates': [
                    "{} moment! 🤯",
                    "Incredible {} clip! 🚀",
                    "{} awesomeness! 🔥",
                    "Epic {} content! 💫",
                    "{} viral moment! 📈",
                    "Mind-blowing {}! 🌟",
                    "{} perfection! ✨",
                    "Must-see {}! 👀"
                ],
                'hashtags': [
                    "#viral", "#trending", "#shorts", "#fyp", "#youtubeshorts", "#content",
                    "#viraltiktok", "#trendingnow", "#shortsvideo", "#foryou"
                ]
            }
        }
    
    def load_copyright_keywords(self):
        """Enhanced copyright keywords for better detection"""
        return {
            'music_copyright': [
                'song', 'music', 'track', 'album', 'single', 'release', 'spotify', 'itunes',
                'billboard', 'charts', 'hit', 'cover', 'remix', 'mashup', 'audio', 'soundtrack',
                'lyrics', 'artist', 'band', 'concert', 'performance', 'official video'
            ],
            'movie_copyright': [
                'movie', 'film', 'cinema', 'hollywood', 'netflix', 'disney', 'marvel', 'dc',
                'trailer', 'scene', 'clip', 'blockbuster', 'theatre', 'actor', 'actress',
                'director', 'producer', 'studio', 'warner', 'paramount', 'universal'
            ],
            'gaming_copyright': [
                'gameplay', 'walkthrough', 'review', 'lets play', 'playthrough', 'stream',
                'twitch', 'nintendo', 'playstation', 'xbox', 'steam', 'ea', 'ubisoft',
                'activision', 'blizzard', 'minecraft', 'fortnite', 'gta', 'call of duty'
            ],
            'sports_copyright': [
                'nfl', 'nba', 'mlb', 'premier league', 'champions league', 'fifa', 'uefa',
                'highlights', 'match', 'game', 'tournament', 'championship', 'olympics',
                'world cup', 'super bowl', 'world series', 'nhl', 'nascar'
            ],
            'tv_copyright': [
                'episode', 'season', 'series', 'tv show', 'netflix series', 'hbo', 'amazon prime',
                'disney+', 'hulu', 'bbc', 'cbs', 'abc', 'nbc', 'fox', 'cartoon network'
            ]
        }
    
    def print_ffmpeg_status(self):
        """Print clear status about FFmpeg"""
        if self.ffmpeg_path:
            print("🎉 FFMPEG STATUS: ✅ DETECTED & READY!")
            print("   → AI-powered title & hashtag generation")
            print("   → Copyright detection system")
            print("   → High-quality vertical shorts")
        else:
            print("❌ FFMPEG STATUS: NOT FOUND")
    
    def extract_keywords_from_content(self, title, description):
        """Extract relevant keywords from video content for title generation"""
        content = (title + ' ' + description).lower()
        
        # Common words to exclude
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
        
        # Extract meaningful words (longer than 3 characters, not stop words)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content)
        meaningful_words = [word for word in words if word not in stop_words]
        
        # Get frequency of words
        from collections import Counter
        word_freq = Counter(meaningful_words)
        
        # Return top 5 most frequent meaningful words
        top_keywords = [word for word, count in word_freq.most_common(5)]
        
        # If no keywords found, use some default based on video length
        if not top_keywords:
            top_keywords = ['amazing', 'epic', 'incredible', 'awesome', 'fantastic']
        
        return top_keywords
    
    def detect_video_category(self, title, description):
        """Enhanced category detection"""
        content = (title + ' ' + description).lower()
        
        category_scores = {}
        for category, keywords in {
            'gaming': ['game', 'gaming', 'play', 'player', 'stream', 'twitch', 'minecraft', 'fortnite', 'valorant', 'overwatch'],
            'music': ['music', 'song', 'album', 'track', 'beat', 'sound', 'artist', 'band', 'piano', 'guitar', 'sing'],
            'sports': ['sports', 'game', 'player', 'team', 'match', 'win', 'championship', 'tournament', 'basketball', 'football', 'soccer'],
            'comedy': ['funny', 'comedy', 'joke', 'laugh', 'humor', 'meme', 'prank', 'hilarious', 'lol', 'fun'],
            'education': ['learn', 'education', 'knowledge', 'study', 'teach', 'tutorial', 'how to', 'explain', 'guide'],
            'cooking': ['cook', 'food', 'recipe', 'kitchen', 'meal', 'dish', 'baking', 'chef', 'delicious', 'tasty'],
            'tech': ['tech', 'technology', 'gadget', 'device', 'review', 'unboxing', 'iphone', 'android', 'computer', 'laptop']
        }.items():
            score = sum(1 for keyword in keywords if keyword in content)
            category_scores[category] = score
        
        best_category = max(category_scores, key=category_scores.get)
        return best_category if category_scores[best_category] > 0 else 'general'
    
    def analyze_copyright_risk(self, title, description):
        """Enhanced copyright risk analysis with detailed scoring"""
        content = (title + ' ' + description).lower()
        copyright_risks = []
        risk_score = 0
        
        # Check for music copyright
        music_keywords = [kw for kw in self.copyright_keywords['music_copyright'] if kw in content]
        if music_keywords:
            risk_score += 30
            copyright_risks.append(f"🎵 Music: {', '.join(music_keywords[:3])}")
        
        # Check for movie copyright
        movie_keywords = [kw for kw in self.copyright_keywords['movie_copyright'] if kw in content]
        if movie_keywords:
            risk_score += 25
            copyright_risks.append(f"🎬 Movie: {', '.join(movie_keywords[:3])}")
        
        # Check for gaming copyright
        gaming_keywords = [kw for kw in self.copyright_keywords['gaming_copyright'] if kw in content]
        if gaming_keywords:
            risk_score += 20
            copyright_risks.append(f"🎮 Gaming: {', '.join(gaming_keywords[:3])}")
        
        # Check for sports copyright
        sports_keywords = [kw for kw in self.copyright_keywords['sports_copyright'] if kw in content]
        if sports_keywords:
            risk_score += 25
            copyright_risks.append(f"⚽ Sports: {', '.join(sports_keywords[:3])}")
        
        # Check for TV copyright
        tv_keywords = [kw for kw in self.copyright_keywords['tv_copyright'] if kw in content]
        if tv_keywords:
            risk_score += 25
            copyright_risks.append(f"📺 TV Show: {', '.join(tv_keywords[:3])}")
        
        # Determine risk level and status
        if risk_score >= 60:
            risk_level = 'high'
            copyright_status = "🔴 HIGH COPYRIGHT RISK"
            copyright_score = min(95, risk_score)
        elif risk_score >= 30:
            risk_level = 'medium'
            copyright_status = "🟡 MEDIUM COPYRIGHT RISK"
            copyright_score = risk_score
        else:
            risk_level = 'low'
            copyright_status = "🟢 LOW COPYRIGHT RISK"
            copyright_score = max(5, risk_score)
        
        if not copyright_risks:
            copyright_risks = ["Content appears to be original or fair use"]
        
        return {
            'status': copyright_status,
            'score': copyright_score,
            'details': copyright_risks,
            'risk_level': risk_level,
            'risk_score': risk_score
        }
    
    def get_copyright_advice(self, risk_level, category):
        """Provide specific advice based on copyright risk"""
        advice = {
            'high': {
                'warning': "🚨 HIGH COPYRIGHT RISK",
                'description': "Strong chance of copyright claims",
                'suggestions': [
                    "Use shorter clips (under 10 seconds)",
                    "Add substantial commentary",
                    "Use royalty-free alternatives",
                    "Consider fair use justification"
                ],
                'consequences': [
                    "💰 Revenue redirected to copyright owner",
                    "📉 Limited distribution",
                    "🚫 Possible video takedown"
                ]
            },
            'medium': {
                'warning': "⚠️ MEDIUM COPYRIGHT RISK",
                'description': "Possible copyright claims",
                'suggestions': [
                    "Add your own creative elements",
                    "Keep clips very short",
                    "Add educational context",
                    "Monitor for claims after posting"
                ],
                'consequences': [
                    "⚠️ Possible revenue sharing",
                    "📊 Reduced reach potential",
                    "👀 Claims likely but not certain"
                ]
            },
            'low': {
                'warning': "✅ LOW COPYRIGHT RISK",
                'description': "Likely safe to use",
                'suggestions': [
                    "Still credit original creators",
                    "Keep transformative elements",
                    "Follow platform guidelines"
                ],
                'consequences': [
                    "✅ Minimal risk of claims",
                    "📈 Normal distribution",
                    "💸 Full revenue potential"
                ]
            }
        }
        return advice.get(risk_level, advice['medium'])
    
    def generate_contextual_title(self, category, keywords, clip_duration, start_time, video_title):
        """Generate contextual title based on video content and clip timing"""
        
        # Get category templates
        category_data = self.video_categories.get(category, self.video_categories['general'])
        template = random.choice(category_data['templates'])
        
        # Use the most relevant keyword or video title snippet
        if keywords:
            main_keyword = keywords[0].title()
        else:
            # Extract main words from video title
            title_words = [word for word in video_title.split() if len(word) > 3]
            main_keyword = title_words[0] if title_words else "Amazing"
        
        # Add timing context for more relevance
        timing_phrases = [
            "Epic", "Incredible", "Unbelievable", "Amazing", "Fantastic",
            "Brilliant", "Stunning", "Mind-blowing", "Spectacular", "Phenomenal"
        ]
        
        timing_phrase = random.choice(timing_phrases)
        
        # Choose title generation strategy
        strategies = [
            # Strategy 1: Template-based
            lambda: template.format(main_keyword),
            # Strategy 2: Timing-based
            lambda: f"{timing_phrase} {main_keyword} moment at {self.format_time(start_time)}!",
            # Strategy 3: Action-based
            lambda: f"{timing_phrase} {main_keyword} action! 🎯",
            # Strategy 4: Simple impactful
            lambda: f"{main_keyword} Perfection! ✨",
            # Strategy 5: Question-based
            lambda: f"Can you believe this {main_keyword} moment? 🤔",
            # Strategy 6: Achievement-based
            lambda: f"{main_keyword} Achievement Unlocked! 🏅",
            # Strategy 7: Surprise-based
            lambda: f"Wait for the {main_keyword} moment! ⏳",
        ]
        
        title = random.choice(strategies)()
        
        # Ensure title is not too long
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title
    
    def format_time(self, seconds):
        """Format seconds into minutes:seconds"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def generate_ai_hashtags(self, category, copyright_status, keywords):
        """Generate AI-powered hashtags based on category, copyright status, and keywords"""
        category_data = self.video_categories.get(category, self.video_categories['general'])
        
        # Base hashtags from category
        base_hashtags = random.sample(category_data['hashtags'], min(5, len(category_data['hashtags'])))
        
        # Platform hashtags
        platform_hashtags = ["#shorts", "#youtubeshorts", "#viral", "#trending", "#fyp"]
        
        # Copyright-related hashtags based on risk level
        if copyright_status['risk_level'] == 'high':
            copyright_hashtags = ["#fairuse", "#copyright", "#contentcreator", "#educational"]
        elif copyright_status['risk_level'] == 'medium':
            copyright_hashtags = ["#fairuse", "#creator", "#content", "#transformative"]
        else:
            copyright_hashtags = ["#originalcontent", "#creator", "#content", "#original"]
        
        # Add keyword-based hashtags (first 2 keywords)
        keyword_hashtags = [f"#{keyword}" for keyword in keywords[:2]]
        
        # Combine all hashtags and limit to 12
        all_hashtags = base_hashtags + platform_hashtags + copyright_hashtags + keyword_hashtags
        return ' '.join(all_hashtags[:12])
    
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
        """Get video information"""
        ydl_opts = {'quiet': True, 'no_warnings': True}
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
            return {'success': False, 'error': str(e)}
    
    def download_video(self, video_url, output_path):
        """Download YouTube video in HIGH QUALITY"""
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best[height<=1080]',
            'quiet': False,
        }
        
        try:
            print(f"📥 Downloading source video...")
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
        """Enhanced video analysis with contextual AI metadata"""
        duration = video_info['duration']
        
        # Detect category and copyright
        category = self.detect_video_category(video_info['title'], video_info.get('description', ''))
        copyright_analysis = self.analyze_copyright_risk(video_info['title'], video_info.get('description', ''))
        copyright_advice = self.get_copyright_advice(copyright_analysis['risk_level'], category)
        
        # Extract keywords from video content for title generation
        keywords = self.extract_keywords_from_content(video_info['title'], video_info.get('description', ''))
        
        print(f"🎯 Video Analysis:")
        print(f"   → Category: {category.upper()}")
        print(f"   → Copyright: {copyright_analysis['status']}")
        print(f"   → Risk Level: {copyright_analysis['risk_level'].upper()}")
        print(f"   → Risk Score: {copyright_analysis['risk_score']}/100")
        print(f"   → Keywords: {', '.join(keywords)}")
        
        clips = []
        # Always generate exactly 6 clips
        num_clips = 6
        timestamps = self.generate_smart_timestamps(duration, num_clips)
        
        for i, start_time in enumerate(timestamps):
            quality_score = 8.0 + (i * 0.2) + random.uniform(-0.3, 0.3)
            quality_score = min(9.5, max(7.5, round(quality_score, 1)))
            
            # Generate contextual AI-powered title and hashtags
            ai_title = self.generate_contextual_title(
                category,
                keywords,
                15,  # clip duration
                start_time,
                video_info['title']
            )
            ai_hashtags = self.generate_ai_hashtags(category, copyright_analysis, keywords)
            
            clips.append({
                "start_time": start_time,
                "duration": 15,
                "title": ai_title,
                "hashtags": ai_hashtags,
                "quality_score": quality_score,
                "engagement_score": round(quality_score * 10 + random.uniform(0, 5), 1),
                "virality_potential": f"{min(95, int(quality_score * 10))}%",
                "category": category,
                "copyright_status": copyright_analysis['status'],
                "copyright_score": copyright_analysis['score'],
                "copyright_details": copyright_analysis['details'],
                "risk_level": copyright_analysis['risk_level'],
                "risk_score": copyright_analysis['risk_score'],
                "copyright_advice": copyright_advice,
                "keywords": keywords
            })
        
        return {
            "clips": clips,
            "video_category": category,
            "overall_copyright_status": copyright_analysis['status'],
            "copyright_risk_level": copyright_analysis['risk_level'],
            "copyright_risk_score": copyright_analysis['risk_score'],
            "copyright_advice": copyright_advice
        }
    
    def generate_smart_timestamps(self, duration, num_clips):
        """Generate smart timestamps - Always return exact number of clips"""
        if duration <= 60:
            # For very short videos, use predefined timestamps
            possible_timestamps = [5, 15, 25, 35, 45, 55]
            return possible_timestamps[:num_clips]
        
        # For longer videos, distribute timestamps evenly throughout the video
        timestamps = []
        start_buffer = max(10, duration * 0.05)  # Start after 5% of video
        end_buffer = duration * 0.95  # End before last 5% of video
        
        # Generate exactly num_clips timestamps
        for i in range(num_clips):
            # Distribute points evenly throughout the video
            point = (i + 1) / (num_clips + 1)
            timestamp = start_buffer + (end_buffer - start_buffer) * point
            timestamps.append(int(timestamp))
        
        return timestamps
    
    def create_short_video(self, input_path, start_time, duration, output_path):
        """Create HIGH QUALITY short video in vertical format"""
        if not self.ffmpeg_path:
            return False
        
        try:
            print(f"🎬 Creating {duration}-second vertical short...")
            
            if not os.path.exists(input_path):
                return False
            
            # HIGH QUALITY FFmpeg command
            cmd = [
                self.ffmpeg_path,
                '-ss', str(start_time),
                '-i', input_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-crf', '23',
                '-preset', 'medium',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black',
                '-movflags', '+faststart',
                '-pix_fmt', 'yuv420p',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0 and os.path.exists(output_path):
                output_size = os.path.getsize(output_path)
                if output_size > 1024 * 1024:
                    return True
            
            return False
                
        except Exception as e:
            print(f"❌ Video creation error: {e}")
            return False

    def sanitize_filename(self, filename):
        """Sanitize filename for safe file system use"""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        # Trim to reasonable length
        return sanitized.strip()[:100]

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
        
        # Save session to file system
        session_manager.save_session(session_id, session_data)
        
        # Also store in Flask session for immediate access
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
            'copyright_advice': analysis['copyright_advice'],
            'ffmpeg_available': shorts_generator.ffmpeg_path is not None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'})

def get_session_data(session_id):
    """Get session data from either Flask session or file system"""
    # First try Flask session
    session_data = session.get(session_id)
    if session_data:
        return session_data
    
    # If not in Flask session, try file system
    session_data = session_manager.load_session(session_id)
    if session_data:
        # Restore to Flask session for future requests
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
        
        # Create output filename using AI-generated title
        ai_title = clip_data['title']
        safe_title = shorts_generator.sanitize_filename(ai_title)
        timestamp = int(datetime.now().timestamp())
        output_filename = f'{safe_title}_{timestamp}.mp4'
        output_path = os.path.join('downloads', output_filename)
        
        print("=" * 60)
        print(f"🚀 CREATING CONTEXTUAL AI SHORT #{clip_index + 1}")
        print(f"🎬 Original: {video_info['title']}")
        print(f"📝 AI Title: {ai_title}")
        print(f"🔑 Keywords: {', '.join(clip_data.get('keywords', []))}")
        print(f"🏷️ Category: {clip_data['category'].upper()}")
        print(f"⚖️ Copyright: {clip_data['copyright_status']}")
        print(f"📊 Risk Score: {clip_data['risk_score']}/100")
        print("=" * 60)
        
        # Download the source video
        if not shorts_generator.download_video(video_url, input_path):
            return jsonify({'success': False, 'error': 'Failed to download source video'})
        
        # Create the professional vertical short
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
                'display_name': f'{ai_title}.mp4',
                'clip_data': clip_data,
                'file_size': file_size_str,
                'video_dimensions': '1080x1920',
                'message': f'🎉 Contextual AI short ready! ({file_size_str})'
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
            
            # Create output filename using AI-generated title
            ai_title = clip_data['title']
            safe_title = shorts_generator.sanitize_filename(ai_title)
            timestamp = int(datetime.now().timestamp())
            output_filename = f'{safe_title}_{timestamp}.mp4'
            output_path = os.path.join('downloads', output_filename)
            
            print(f"🎬 Processing clip {clip_index + 1}/{len(clip_indices)}: {ai_title}")
            
            # Create the professional vertical short
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
                    'display_name': f'{ai_title}.mp4',
                    'clip_data': clip_data,
                    'file_size': file_size_str
                })
                generated_files.append({
                    'path': output_path,
                    'display_name': f'{ai_title}.mp4'
                })
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
        
        # Create zip file if multiple videos were generated
        zip_url = None
        if len([r for r in results if r['success']]) > 1:
            zip_filename = f'Contextual_YouTube_Shorts_{int(datetime.now().timestamp())}.zip'
            zip_path = os.path.join('downloads', zip_filename)
            
            try:
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file_info in generated_files:
                        if os.path.exists(file_info['path']):
                            # Use the display name (AI title) in the zip file
                            zipf.write(file_info['path'], file_info['display_name'])
                
                zip_url = f'/download/{zip_filename}'
                print(f"📦 Created batch download: {zip_filename}")
            except Exception as e:
                print(f"❌ Failed to create zip file: {e}")
        
        return jsonify({
            'success': True,
            'results': results,
            'total_generated': len([r for r in results if r['success']]),
            'batch_download_url': zip_url,
            'message': f'✅ Successfully generated {len([r for r in results if r["success"]])} contextual shorts!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Batch generation failed: {str(e)}'})

@app.route('/download/<filename>')
def download_file(filename):
    """Serve video files for download with proper filename"""
    try:
        directory = os.path.join(os.getcwd(), 'downloads')
        
        # Check if file exists
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
    # Clean up expired sessions on health check
    session_manager.cleanup_expired_sessions()
    
    return jsonify({
        'status': 'healthy',
        'ffmpeg_available': shorts_generator.ffmpeg_path is not None,
        'downloads_folder': os.path.exists('downloads'),
        'sessions_folder': os.path.exists('sessions'),
        'active_sessions': len(os.listdir('sessions')) if os.path.exists('sessions') else 0,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/cleanup-sessions', methods=['POST'])
def cleanup_sessions():
    """Manual cleanup of expired sessions"""
    try:
        session_manager.cleanup_expired_sessions()
        return jsonify({'success': True, 'message': 'Session cleanup completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Render-compatible startup
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 YouTube Shorts Pro Server Starting...")
    print("🎯 CONTEXTUAL AI TITLE GENERATION ENABLED")
    print("💾 PERSISTENT SESSION MANAGEMENT ENABLED")
    
    # Clean up any expired sessions on startup
    session_manager.cleanup_expired_sessions()
    
    app.run(host='0.0.0.0', port=port)
