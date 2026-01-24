"""
LangChain service for AI-powered job analysis and career planning.
Generates competitive reports with learning plans and required skills using streaming.
"""
import os
import logging
import json
from typing import List, Dict, AsyncGenerator, Any
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool
from langchain.agents import create_agent
from services.data_service import get_data_service

logger = logging.getLogger(__name__)


class JobAnalysisService:
    """Service for analyzing job postings using LangChain with streaming support"""

    def __init__(self):
        """Initialize the LangChain service with LLM configuration."""
        self._init_config()
        self._init_llm()
        logger.info(f"JobAnalysisService initialized with model: {self.model_name}")

    def _init_config(self):
        """Load configuration from environment variables."""
        self.api_key = os.getenv("LLM_API_KEY")
        self.api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

        # Validate and set temperature with proper range checking
        temp_str = os.getenv("LLM_TEMPERATURE", "0.7")
        try:
            self.temperature = float(temp_str)
            if not 0.0 <= self.temperature <= 2.0:
                logger.warning(f"Temperature {self.temperature} out of range [0.0, 2.0], using default 0.7")
                self.temperature = 0.7
        except ValueError:
            logger.warning(f"Invalid temperature value '{temp_str}', using default 0.7")
            self.temperature = 0.7

        if not self.api_key:
            logger.error("LLM_API_KEY not found in environment variables")
            raise ValueError("LLM_API_KEY is required but not set")

        # Validate API base URL format
        if self.api_base and not (self.api_base.startswith("http://") or self.api_base.startswith("https://")):
            logger.error(f"Invalid LLM_API_BASE format: {self.api_base}")
            raise ValueError("LLM_API_BASE must be a valid URL starting with http:// or https://")

    def _init_llm(self):
        """Initialize LLM and base components."""
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.api_base,
            temperature=self.temperature,
            max_tokens=4000,
            streaming=True
        )
        self.str_parser = StrOutputParser()
        self.data_service = get_data_service()

    def _format_job_data(self, jobs: List[Dict]) -> str:
        """Format job data for the LLM prompt."""
        formatted_jobs = []
        for i, job in enumerate(jobs, 1):
            # Safely truncate job description to avoid errors
            job_desc = job.get('job_desc', 'N/A')
            if job_desc and isinstance(job_desc, str) and len(job_desc) > 500:
                job_desc = job_desc[:500] + "..."
            elif not isinstance(job_desc, str):
                job_desc = 'N/A'

            job_text = f"""
## Job {i}:
- Position: {job.get('job_name', 'N/A')}
- Company: {job.get('company_name', 'N/A')}
- Location: {job.get('city', 'N/A')} ({job.get('district', 'N/A')})
- Salary: {job.get('salary_raw', 'N/A')}
- Experience: {job.get('experience_raw', 'N/A')}
- Education: {job.get('education', 'N/A')}
- Skills: {job.get('skills_tags', 'N/A')}
- Description: {job_desc}
"""
            formatted_jobs.append(job_text)
        return "\n".join(formatted_jobs)

    def _clean_json_response(self, text: str) -> str:
        """Remove markdown code blocks from LLM response."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _validate_jobs_input(self, jobs: List[Dict]) -> None:
        """Validate jobs list structure and content."""
        if not isinstance(jobs, list):
            raise ValueError("jobs must be a list")

        if len(jobs) > 1000:
            raise ValueError(f"Too many jobs provided (max 1000, got {len(jobs)})")

        required_fields = ['job_name', 'company_name']
        for i, job in enumerate(jobs):
            if not isinstance(job, dict):
                raise ValueError(f"Job at index {i} must be a dictionary")

            # Check for at least some required fields
            if not any(field in job for field in required_fields):
                logger.warning(f"Job at index {i} missing required fields: {required_fields}")

    def _sanitize_user_prompt(self, user_prompt: str) -> str:
        """Sanitize user prompt to prevent prompt injection."""
        if user_prompt is None:
            return None

        if not isinstance(user_prompt, str):
            raise ValueError("user_prompt must be a string")

        # Limit prompt length
        max_length = 2000
        if len(user_prompt) > max_length:
            logger.warning(f"user_prompt truncated from {len(user_prompt)} to {max_length} chars")
            user_prompt = user_prompt[:max_length]

        # Remove potentially dangerous patterns
        dangerous_patterns = ['<system>', '<instruction>', '<admin>']
        for pattern in dangerous_patterns:
            if pattern.lower() in user_prompt.lower():
                logger.warning(f"Removed potentially dangerous pattern from user_prompt: {pattern}")
                user_prompt = user_prompt.replace(pattern, '').replace(pattern.lower(), '')

        return user_prompt.strip()

    def _is_thinking_content(self, full_response: str) -> bool:
        """
        Determine if current response is inside thinking/reasoning tags.

        Some models (like DeepSeek) output reasoning in special tags.
        Returns True if we're inside an unclosed thinking tag.
        """
        # Count opening and closing tags
        # The tags appear to be special Chinese characters used by certain models
        open_tag = "````"
        close_tag = "```"

        open_count = full_response.count(open_tag)
        close_count = full_response.count(close_tag)

        # If we have more opening tags than closing tags, we're still "thinking"
        return open_count > close_count

    def _parse_llm_response(self, text: str, jobs_count: int) -> Dict[str, Any]:
        """Parse the raw LLM response into a structured dictionary."""
        try:
            cleaned = self._clean_json_response(text)
            result = json.loads(cleaned)
            
            # Add metadata
            result["metadata"] = {
                "jobs_analyzed": jobs_count,
                "analysis_date": datetime.now().isoformat(),
                "model_used": self.model_name,
            }
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "raw_response": text,
                "metadata": {
                    "jobs_analyzed": jobs_count,
                    "analysis_date": datetime.now().isoformat(),
                    "note": "无法解析为结构化 JSON，返回原始响应"
                }
            }

    async def analyze_jobs_streaming(self, jobs: List[Dict], user_prompt: str = None) -> AsyncGenerator[str, None]:
        """Stream job analysis results in real-time using SSE events."""
        if not jobs:
            yield json.dumps({"type": "error", "message": "没有职位信息可供分析"}, ensure_ascii=False)
            return

        # Validate and sanitize inputs
        try:
            self._validate_jobs_input(jobs)
            user_prompt = self._sanitize_user_prompt(user_prompt)
        except ValueError as e:
            yield json.dumps({"type": "error", "message": f"输入验证失败: {str(e)}"}, ensure_ascii=False)
            return

        try:
            # Define tools
            # Define tools with rich descriptions to help LLM decide when to call them
            @tool
            def get_skill_statistics() -> str:
                """
                对当前检索到的所有职位（全量数据）执行深度的技术栈统计分析。
                当你需要提供真实的市场技术趋势、核心技能频率占比、或需要量化数据来支持你的职业路径建议时，请调用此工具。
                注意：此工具处理的是后台全量数据集，比你上下文中的部分摘要信息更全面。
                """
                counts = self.data_service.extract_skills(jobs)
                sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
                top_skills = [{"skill": s, "count": c} for s, c in sorted_counts]
                return json.dumps(top_skills, ensure_ascii=False)

            tools = [get_skill_statistics]
            
            # Professional, goal-oriented system prompt
            system_prompt = """你是一位顶尖的职业规划专家和资深技术招聘经理。
            
            # 你的核心能力:
            1. **事实检索**: 你能通过下方的职位快照快速建立对垂直领域的初步认知。
            2. **专家级统计分析**: 你配备了 `get_skill_statistics` 工具。它能深度扫描后台成百上千条原始招聘数据。
            **调用策略**:
            - **必须调用**: 当用户需要“精确统计”、“热度排名”、“技能占比”或询问“全量市场趋势”时。
            - **无需调用**: 如果用户的问题仅仅是基于当前可见的职位摘要（Job Snapshot）进行总结、规划或简单建议，或者你认为当前信息已足够给出专业回答，则应直接回答，避免过度使用工具。
            
            # 业务上下文 (职位片段):
            {job_summary}
            
            # 输出规范:
            1. **最终报告模块**: 如果你生成的是一份全面的发展报告，请在回复的最末尾附带一个遵循以下结构的 JSON 代码块（放在 ```json 标签内）。这将用于驱动前端的可视化图表。
            2. **语气**: 保持专业、犀利且富有启发性。
            3. **语言**: 必须使用中文回答。
            
            # 期待的 JSON 结构 (仅在生成最终报告时包含):
            {{
              "summary": "基于全量数据分析的市场综述",
              "key_skills": ["具体技能1", "具体技能2"],
              "soft_skills": ["能力1", "能力2"],
              "learning_plan": [
                {{
                  "phase": "阶段名称",
                  "duration": "预估周期",
                  "objectives": ["核心目标"],
                  "skills": ["学习重点"],
                  "projects": ["实战项目建议"],
                  "resources": [{{"name": "资源名称", "type": "类型", "description": "简述"}}]
                }}
              ],
              "salary_insights": "具有洞察力的薪资趋势分析",
              "career_path": "建议的进阶演进路径"
            }}
            """

            job_summary = self._format_job_data(jobs[:5])
            
            agent_executor = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=system_prompt.format(job_summary=job_summary)
            )

            input_text = user_prompt if user_prompt else "请根据提供的职位信息，为我生成一份全面的职业发展分析报告。"
            
            yield json.dumps({"type": "status", "message": "正在初始化分析流程...", "progress": 5}, ensure_ascii=False)

            # Execution with manual step handling to yield intermediate results
            full_response = ""
            async for event in agent_executor.astream_events(
                {"messages": [("user", input_text)]},
                version="v1"
            ):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        # Check for thinking/reasoning content (specific models like DeepSeek)
                        reasoning = ""
                        if hasattr(chunk, "additional_kwargs"):
                            reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                        
                        content = chunk.content
                        
                        if reasoning:
                            yield json.dumps({"type": "chunk", "content": reasoning, "is_thought": True}, ensure_ascii=False)
                        
                        if content:
                            full_response += content
                            # Determine if this content is inside thinking/reasoning tags
                            # Some models use special tags for reasoning that should be displayed differently
                            is_thought = self._is_thinking_content(full_response)
                            yield json.dumps({"type": "chunk", "content": content, "is_thought": is_thought}, ensure_ascii=False)
                
                elif kind == "on_tool_start":
                    yield json.dumps({
                        "type": "tool_start",
                        "tool": event["name"],
                        "input": event["data"].get("input"),
                        "message": f"正在调用工具: {event['name']}..."
                    }, ensure_ascii=False)
                
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    if hasattr(output, "content"):
                        output = output.content
                    
                    yield json.dumps({
                        "type": "tool_end",
                        "tool": event["name"],
                        "output": output,
                        "message": f"工具 {event['name']} 执行完毕"
                    }, ensure_ascii=False)
            
            # Try to parse the final response as JSON for the structured report card
            report_data = None
            try:
                # Remove any thinking tags for parsing
                clean_text = full_response
                if "<think>" in clean_text and "</think>" in clean_text:
                    parts = clean_text.split(r"</think>")
                    if len(parts) > 1:
                        clean_text = parts[-1]
                
                cleaned_json = self._clean_json_response(clean_text)
                if cleaned_json and (cleaned_json.startswith("{") or cleaned_json.startswith("[")):
                    report_data = self._parse_llm_response(cleaned_json, len(jobs))
            except Exception as e:
                logger.warning(f"Failed to parse structured report from response: {e}")

            yield json.dumps({
                "type": "complete", 
                "message": "分析完成", 
                "progress": 100,
                "data": report_data
            }, ensure_ascii=False)
            logger.info(f"Successfully completed agentic analysis of {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"Error during streaming analysis: {e}", exc_info=True)
            yield json.dumps({"type": "error", "message": str(e), "progress": 0}, ensure_ascii=False)


# Singleton instance
_job_analysis_service = None

def get_job_analysis_service() -> JobAnalysisService:
    """Get or create the singleton JobAnalysisService instance."""
    global _job_analysis_service
    if _job_analysis_service is None:
        _job_analysis_service = JobAnalysisService()
    return _job_analysis_service
