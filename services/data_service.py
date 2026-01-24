"""
Data service for job data processing, skill extraction, and visualization.
"""
import logging
import re
import json
import base64
import os
from io import BytesIO
from collections import Counter
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from wordcloud import WordCloud

logger = logging.getLogger(__name__)

class DataService:
    """Service handling data processing, skill analysis, and visualization logic."""

    @staticmethod
    def get_font_path() -> str:
        """Find a suitable font path for word cloud generation (supports Chinese)."""
        possible_fonts = [
            'C:/Windows/Fonts/msyh.ttc',  # Microsoft YaHei (Windows)
            'C:/Windows/Fonts/simhei.ttf',  # SimHei (Windows)
            '/System/Library/Fonts/PingFang.ttc',  # PingFang (macOS)
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux
        ]
        for font in possible_fonts:
            if os.path.exists(font):
                return font
        return None

    @classmethod
    def generate_wordcloud(cls, skill_counts: dict, width: int = 800, height: int = 400) -> str:
        """
        Generate word cloud image (Base64) from skill frequency data.
        """
        if not skill_counts:
            return None

        try:
            font_path = cls.get_font_path()
            
            wc_params = {
                "width": width,
                "height": height,
                "background_color": 'white',
                "colormap": 'viridis',
                "max_words": 100,
                "relative_scaling": 0.5,
                "min_font_size": 10,
            }
            
            if font_path:
                wc_params["font_path"] = font_path
                logger.info(f"Using font for wordcloud: {font_path}")
            else:
                logger.warning("No Chinese font found for wordcloud")

            wordcloud = WordCloud(**wc_params).generate_from_frequencies(skill_counts)

            # Create figure
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            ax.set_title('AI Agent Skills Word Cloud', fontsize=16, pad=20, fontfamily='sans-serif')

            # Save to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            plt.close(fig)

            return base64.b64encode(buf.read()).decode('utf-8')

        except Exception as e:
            logger.error(f"Error generating word cloud: {e}")
            return None

    @staticmethod
    def extract_skills(jobs: list) -> dict:
        """
        Extract and count skills from job postings.
        """
        all_skills = []
        cn_keywords = ["大模型", "深度学习", "机器学习", "自然语言处理", "图像识别", "算法"]
        stop_words = {'and', 'the', 'with', 'to', 'of', 'in', 'for', 'boss', 'kanzhun', 'api', 'agent', 'ai'}

        for job in jobs:
            # 1. From skills_tags
            tags_raw = job.get('skills_tags')
            if tags_raw:
                try:
                    tags = json.loads(tags_raw)
                    if isinstance(tags, list):
                        all_skills.extend([tag.lower() for tag in tags])
                except:
                    pass

            # 2. From job_desc
            desc = job.get('job_desc', '')
            if desc:
                # English keywords
                eng_words = re.findall(r'[a-zA-Z0-9+#]+', desc)
                all_skills.extend([w.lower() for w in eng_words if len(w) > 1 and not w.isdigit()])
                
                # Chinese keywords
                for kw in cn_keywords:
                    if kw in desc:
                        all_skills.append(kw)

        skill_counts = Counter(all_skills)
        # Filter stop words
        return {k: v for k, v in skill_counts.items() if k not in stop_words}

# Singleton instance
_data_service = DataService()

def get_data_service() -> DataService:
    return _data_service
