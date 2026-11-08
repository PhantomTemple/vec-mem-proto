import json
import os
import math
import requests
from typing import List, Dict

# ========== 配置区 ==========
OLLAMA_BASE = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
MEMORY_PATH = "vector_memory.json"
SIM_THRESHOLD = 0.65

# 余弦相似度计算
def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(x*x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot/(norm_a*norm_b)

# 获取文本向量（新版 /api/embed，带异常捕获+超时）
def get_embedding(text: str) -> List[float] | None:
    try:
        res = requests.post(
            f"{OLLAMA_BASE}/api/embed",
            json={"model": EMBED_MODEL, "input": text},
            timeout=30
        )
        res.raise_for_status()
        data = res.json()
        return data["embeddings"][0]
    except requests.exceptions.RequestException:
        return None

# 初始化记忆文件
def init_memory():
    if not os.path.exists(MEMORY_PATH):
        data = {"memories": []}
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def save_memory(mem_list):
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump({"memories": mem_list}, f, ensure_ascii=False, indent=2)

def load_memory() -> List[Dict]:
    if not os.path.exists(MEMORY_PATH):
        return []
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["memories"]

# 新增记忆，永久保存
def add_memory(content: str, tag: str = "general") -> bool:
    emb = get_embedding(content)
    if emb is None:
        return False
    mems = load_memory()
    mems.append({
        "content": content,
        "tag": tag,
        "embedding": emb,
        "access": 0
    })
    save_memory(mems)
    return True

# 语义召回，无自动遗忘
def recall_memory(query: str, top_k=3) -> List[Dict]:
    q_emb = get_embedding(query)
    if q_emb is None:
        return []
    mems = load_memory()
    scored = []
    for m in mems:
        sim = cosine_sim(q_emb, m["embedding"])
        scored.append((sim, m))
    scored = sorted(scored, key=lambda x:x[0], reverse=True)
    out = []
    for s,item in scored:
        if s >= SIM_THRESHOLD and len(out) < top_k:
            item["access"] += 1
            out.append(item)
    save_memory(mems)
    return out

# 拼接上下文prompt
def build_context_prompt(user_msg: str) -> str:
    hits = recall_memory(user_msg)
    if not hits:
        recall_block = "【长期记忆】无相关记忆"
    else:
        recall_block = "【长期记忆】\n" + "\n".join([f"- {x['content']}" for x in hits])
    final = f"""
{recall_block}
用户提问：{user_msg}
"""
    return final

if __name__ == "__main__":
    init_memory()
    # add_memory("这里填写你要记住的内容")
    print(build_context_prompt("你的问题"))
