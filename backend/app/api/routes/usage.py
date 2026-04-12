from fastapi import APIRouter

from backend.app.modules.agent.tools.tavily_stats import get_tavily_usage_snapshot

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
async def usage() -> dict:
    """
    聚合用量（与是否配置 Tavily 无关；未配置时 `tavily.configured` 为 false）。
    Tavily 每次调用仍写入 `ace_claw` 日志。
    """
    return {
        "tavily": get_tavily_usage_snapshot(),
    }
