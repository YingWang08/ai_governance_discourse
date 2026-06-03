import pandas as pd, os

SAMPLE = os.path.join("..", "output", "tables", "coding_sample.csv")
df = pd.read_csv(SAMPLE, dtype=str)

drop = [c for c in ["llm_label", "llm_label_run2"] if c in df.columns]
if drop:
    df = df.drop(columns=drop)
    df.to_csv(SAMPLE, index=False)
    print(f"已删除列：{drop}")
else:
    print("没有找到 llm_label / llm_label_run2，无需处理")

print("当前 llm_ 开头的列：", [c for c in df.columns if c.startswith("llm_")])