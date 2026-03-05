from openai import OpenAI

client = OpenAI(
base_url = "https://integrate.api.nvidia.com/v1",
api_key = "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"
)

completion = client.chat.completions.create(
model="openai/gpt-oss-120b",
messages=[{"role":"user","content":""}],
temperature=1,
top_p=1,
max_tokens=4096,
stream=True
)

for chunk in completion:
if not getattr(chunk, "choices", None):
continue
reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
if reasoning:
print(reasoning, end="")
if chunk.choices and chunk.choices[0].delta.content is not None:
print(chunk.choices[0].delta.content, end="")
