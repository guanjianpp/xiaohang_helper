import requests
import streamlit as st
from pathlib import Path
from prompts import load_school_info, get_system_prompt
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-mauksldaewhbllokrwtpnmrzpukyehpshfadzclxoqxwrrpn"
HEADERS = {
"Authorization": f"Bearer {API_KEY}",
"Content-Type": "application/json",
}
st.divider()
st.header("📞 电话黄页（静态兜底）")
st.caption("AI 答不上来时，可以直接查这里")

yellow_page = """
| 部门 | 电话 |
|------|------|
| 校园 110（保卫处 24h） | 0371-61916110 ⚠ 以官方为准 |
| 学校总值班室 | 0371-61911000 ⚠ 以官方为准 |
| 后勤管理处 | 0371-61912800 ⚠ 以官方为准 |
| 后勤服务热线/物业报修 | 0371-61913110 ⚠ 以官方为准 |
| 校医院急诊（24h） | 0371-61912730 ⚠ 以官方为准 |
| 招生办公室 | 0371-61916161 ⚠ 以官方为准 |
| 信息管理中心（网信中心） | 0371-61912718 ⚠ 以官方为准 |
"""
st.markdown(yellow_page)
st.title("小航 · 郑州航院校园信息助手")
role = st.selectbox("你是?", ["新生", "在校生", "教师"])
question = st.text_input("有啥想问的?")
PRESET_QUESTIONS = {
"新生": [
"报到那天先去哪?",
"学费什么时候交?",
"宿舍是 4 人间还是 6 人间?",
"有人冒充辅导员要钱怎么办?",
],
"在校生": [

"怎么开在读证明?",
"校园卡丢了怎么补?",
"转专业怎么转?",
"图书馆几点关?",
],
"教师": [
"差旅怎么报销?",
"调课怎么申请?",
"教室设备坏了找谁?",
"科研项目去哪申报?",
],
}
st.markdown("**试试这些问题：**")
cols = st.columns(4)
questions = PRESET_QUESTIONS.get(role, [])
for i, q in enumerate(questions):
    with cols[i % 4]:
        if st.button(q, key=f"q_{i}"):
            st.session_state["question"] = q
            st.rerun()
if question:
    data = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": [
            {"role": "system", "content": get_system_prompt(role, load_school_info())},
            {"role": "user", "content": question},
        ],
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=data, timeout=30)
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        st.write(answer)

    except requests.exceptions.Timeout:
        st.error("AI 响应超时，请稍后再试")
    except requests.exceptions.ConnectionError:
        st.error("网络连接失败，请检查网络")
    except Exception as e:
        st.error(f"发生错误：{e}")