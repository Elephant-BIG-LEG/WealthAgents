from dataclasses import dataclass
from typing import Optional, Dict, Any

# 定义数据源


@dataclass
class Source:
    source_id: str
    source_name: str
    type: str
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
