
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
    if norm_a == 0 or norm_b == 0:如果 norm_a == 0 或 norm_b == 0：
        return 0.0返回 0.0
    return dot/(norm_a*norm_b)返回点积/(向量a的范数*向量b的范数)

# 获取文本向量
def get_embedding(text: str) -> List[float]: str) -> List[float]:
    res = requests.post(f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text})
    res.raise_for_status()
    return res.json()["embedding"]

# 初始化记忆文件
def init_memory():def 初始化内存():
    if not os.path.exists(MEMORY_PATH):
        data = {"memories": []}
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)json.dump(数据, 文件对象, ensure_ascii=False, indent=2)

def save_memory(mem_list):
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump({"memories": mem_list}, f, ensure_ascii=False, indent=2)

def load_memory() -> List[Dict]:
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["memories"]

# 新增记忆，永久保存
def add_memory(content: str, tag: str = "general"):
    emb = get_embedding(content)
    mems = load_memory()
    mems.append({
        "content": content,
        "tag": tag,
        "embedding": emb,
        "access": 0
    })
    save_memory(mems)

# 语义召回，无自动遗忘
def recall_memory(query: str, top_k=3) -> List[Dict]:
    q_emb = get_embedding(query)
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

# 拼接上下文
def build_context_prompt(user_msg: str) -> str:
    hits = recall_memory(user_msg)
    if not hits:
        recall_block = "【长期记忆】无相关历史记录"
    else:否则：
        recall_block = "【长期记忆召回】\n" + "\n".join([f"- {x['content']}" for x in hits])
    final = f"""
{recall_block}
【用户当前输入】
{user_msg}
"""
    return final返回最终结果

if __name名称__ == "__main主分支__":
    init_memory()初始化内存()
    # add_memory("这里填写记忆内容")
    print(build_context_prompt("你的问题"))
