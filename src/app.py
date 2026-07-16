import requests
import streamlit as st
import time
from pathlib import Path
# 修复导入路径，适配项目src结构
from prompts import load_school_info, get_system_prompt

# 全局API配置
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-mauksldaewhbllokrwtpnmrzpukyehpshfadzclxoqxwrrpn"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
# 自定义提问最大字符阈值，可自行调整
MAX_QUESTION_LENGTH = 400

# 会话状态初始化（必须放在最前面，解决按钮填充报错 + 知识库缓存防溢出）
if "question" not in st.session_state:
    st.session_state["question"] = ""
if "answer_cache" not in st.session_state:
    st.session_state["answer_cache"] = ""
# 新增：多轮对话历史存储（挑战1需求）
if "messages" not in st.session_state:
    st.session_state["messages"] = []
# 新增：问答历史记录存储（截图代码）
if "history" not in st.session_state:
    st.session_state["history"] = []
# 一次性加载知识库并截断长度，防止上下文溢出乱码
if "school_data" not in st.session_state:
    full_text = load_school_info()
    st.session_state["school_data"] = full_text[:6000]

# 页面标题
st.title("小航 · 郑州航院校园信息助手")

# 新增：新对话清空按钮（挑战1需求）
if st.button(" 开启新对话", type="primary"):
    st.session_state["messages"] = []
    st.session_state["history"] = []
    st.session_state["question"] = ""
    st.session_state["answer_cache"] = ""
    st.rerun()

# 身份选择
role = st.selectbox("你是?", ["新生", "在校生", "教师"])

# 输入框：绑定会话，按钮点击自动填充
user_input = st.text_input("有啥想问的?", value=st.session_state["question"])
# 手动输入同步更新会话
if user_input != st.session_state["question"]:
    st.session_state["question"] = user_input

# 预设快捷提问按钮
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
            # 赋值问题+清空旧回答+刷新页面填充输入框
            st.session_state["question"] = q
            st.session_state["answer_cache"] = ""
            st.rerun()

st.divider()
question = st.session_state["question"]
if question and question.strip():
    # 新增：提前校验提问长度，过长直接提示，不调用API
    if len(question) > MAX_QUESTION_LENGTH:
        st.error(f"提问文字过长！当前{len(question)}字，最多允许{MAX_QUESTION_LENGTH}字，请精简你的问题后重试")
    else:
        files = list(Path("data").glob("*.md"))
        if not files:
            st.warning("数据文件缺失，请补齐 data/ 目录下的 md 文件")
        else:
            # 组装消息：系统提示词 + 历史对话 + 当前用户提问（挑战1需求）
            messages = [
                           {"role": "system", "content": get_system_prompt(role, st.session_state["school_data"])}
                       ] + st.session_state["messages"]
            messages.append({"role": "user", "content": question})

            data = {
                "model": "deepseek-ai/DeepSeek-V4-Pro",
                "messages": messages,
            }
            try:
                # 新增：加载状态spinner，包裹API请求全部逻辑
                with st.spinner("小航正在思考..."):
                    response = requests.post(API_URL, headers=HEADERS, json=data, timeout=30)
                if response.status_code == 401:
                    st.error("API Key 失效，请联系老师重新获取")
                else:
                    result = response.json()
                    raw_ans = result["choices"][0]["message"]["content"]

                    filter_words = [
                        "Begin gunman",
                        "0371--11",
                        "\"31\":\"3371-669",
                        "11身份证",
                        "我在郑州东站应该怎么去乘坐地铁到"
                    ]
                    clean_ans = raw_ans
                    # 过滤无效乱码片段
                    for word in filter_words:
                        if word in clean_ans:
                            clean_ans = clean_ans.split(word)[0].strip()
                    # 去除重复叠加的来源标记
                    while "[来源:新生入学.md][来源:新生入学.md]" in clean_ans:
                        clean_ans = clean_ans.replace("[来源:新生入学.md][来源:新生入学.md]", "[来源:新生入学.md]")
                    while "[来源:办事流程.md][来源:办事流程.md]" in clean_ans:
                        clean_ans = clean_ans.replace("[来源:办事流程.md][来源:办事流程.md]", "[来源:办事流程.md]")
                    while "[来源:电话黄页.md][来源:电话黄页.md]" in clean_ans:
                        clean_ans = clean_ans.replace("[来源:电话黄页.md][来源:电话黄页.md]", "[来源:电话黄页.md]")
                    while "[来源:应急防骗.md][来源:应急防骗.md]" in clean_ans:
                        clean_ans = clean_ans.replace("[来源:应急防骗.md][来源:应急防骗.md]", "[来源:应急防骗.md]")
                    # ======================================================================

                    st.session_state["answer_cache"] = clean_ans
                    # 挑战1：本轮问答存入多轮对话messages
                    st.session_state["messages"].append({"role": "user", "content": question})
                    st.session_state["messages"].append({"role": "assistant", "content": clean_ans})
                    # 截图代码：保存完整问答历史（带时间、身份）
                    st.session_state["history"].append({
                        "time": time.strftime("%H:%M:%S"),
                        "role": role,
                        "question": question,
                        "answer": clean_ans,
                    })
            except requests.exceptions.Timeout:
                st.error("AI 响应超时，请精简问题或稍后再试")
            except requests.exceptions.ConnectionError:
                st.error("网络连接失败，请检查网络")
            except (KeyError, IndexError):
                st.error("AI 返回格式异常，请重试")
            except Exception as e:
                st.error(f"发生错误：{e}")

# 渲染AI回答
if st.session_state["answer_cache"]:
    st.subheader("小航回答")
    st.write(st.session_state["answer_cache"])

# 截图代码：页面下方展示问答历史 + 新增清空历史按钮
st.divider()
# 左右分栏：标题 + 清空历史按钮
col1, col2 = st.columns([4, 1])
with col1:
    st.header("问答历史")
with col2:
    if st.button("清空历史"):
        st.session_state["history"] = []
        st.rerun()

for item in reversed(st.session_state["history"]):
    st.write(f"[{item['time']}] {item['role']} 提问: {item['question']}")
    st.write(f"回答: {item['answer']}")
    st.caption("---")

# 底部静态电话黄页
st.divider()

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