
import streamlit as st
import re
import csv
import io
import threading

st.set_page_config(
    page_title="Group Dictation Challenge",
    page_icon="📝",
    layout="centered"
)

# =====================================
# 1. 기본 설정
# =====================================

TEACHER_PASSWORD = "1201"
GROUP_COUNT = 7

DEFAULT_PASSAGE = """On New Year’s Eve, Emily was cleaning her room when she discovered an old notebook under her desk. Inside, she found a list of New Year’s resolutions she had written a year earlier: exercise every morning, read thirty books, and improve her English.

However, she had given up on most of her goals before February. “Why did I fail to keep my promises?” she wondered. She realized that her goals had been too ambitious, and she had expected immediate results.

During dinner, Emily shared her concerns with her older brother. He listened carefully and said, “You don’t have to change your entire life overnight. Why don’t you start with something small?”

His advice inspired her to make a more realistic plan. Instead of exercising every morning, she would take a twenty-minute walk three times a week. Instead of reading thirty books, she would read ten pages a day. She also decided to keep an English diary every weekend.

Emily knew that following her new plan wouldn’t always be easy; there would be challenges, unexpected events, and moments when she wanted to give up. However, she promised herself that she would keep trying, even if she made mistakes.

As the clock struck midnight, Emily opened her notebook and wrote one final sentence: “This year, I don’t have to be perfect. I just have to be better than I was yesterday!”"""


# =====================================
# 2. 공유 데이터
# =====================================

@st.cache_resource
def get_shared_data():
    return {
        "passage": DEFAULT_PASSAGE,
        "answers": {f"Group {i}": "" for i in range(1, 8)},
        "finished": False,
        "revealed": False,
        "lock": threading.RLock()
    }

data = get_shared_data()


# =====================================
# 3. 단어 정규화
# =====================================

def normalize_word(word):
    word = word.replace("’", "'").replace("‘", "'")
    return re.sub(r"[^\w'-]", "", word).casefold()


# =====================================
# 4. 편집 거리 기반 채점
# =====================================

def calculate_score(original, answer):

    original_words = original.split()
    answer_words = answer.split()

    a = [normalize_word(w) for w in original_words]
    b = [normalize_word(w) for w in answer_words]

    n = len(a)
    m = len(b)

    # 편집 거리 행렬
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i

    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):

            cost = 0 if a[i - 1] == b[j - 1] else 1

            dp[i][j] = min(
                dp[i - 1][j] + 1,       # 단어 누락
                dp[i][j - 1] + 1,       # 단어 추가
                dp[i - 1][j - 1] + cost # 단어 교체
            )

    # 최적 정렬 역추적
    details = []
    i, j = n, m
    correct = 0
    errors = 0

    while i > 0 or j > 0:

        if (
            i > 0 and j > 0
            and a[i - 1] == b[j - 1]
            and dp[i][j] == dp[i - 1][j - 1]
        ):
            details.append({
                "status": "correct",
                "original": original_words[i - 1],
                "answer": answer_words[j - 1]
            })
            correct += 1
            i -= 1
            j -= 1

        elif (
            i > 0 and j > 0
            and dp[i][j] == dp[i - 1][j - 1] + 1
        ):
            details.append({
                "status": "incorrect",
                "original": original_words[i - 1],
                "answer": answer_words[j - 1]
            })
            errors += 1
            i -= 1
            j -= 1

        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            details.append({
                "status": "missing",
                "original": original_words[i - 1],
                "answer": "(누락)"
            })
            errors += 1
            i -= 1

        else:
            details.append({
                "status": "extra",
                "original": "(없음)",
                "answer": answer_words[j - 1]
            })
            errors += 1
            j -= 1

    details.reverse()

    # 전체 정답 단어와 학생 입력 단어 중 긴 쪽을 기준으로 정확성 계산
    denominator = max(n, m, 1)

    accuracy = round(
        max(0, 100 * (1 - errors / denominator)),
        1
    )

    return correct, denominator, accuracy, details, errors


# =====================================
# 5. 화면 선택
# =====================================

st.title("📝 Group Dictation Challenge")
st.caption("Read · Remember · Reconstruct")

mode = st.radio(
    "접속 화면",
    ["학생용", "교사용"],
    horizontal=True
)

st.divider()


# =====================================
# 6. 학생용
# =====================================

if mode == "학생용":

    st.header("👥 Group Submission")

    with data["lock"]:
        finished = data["finished"]
        revealed = data["revealed"]

    # 활동 종료 후 결과 공개
    if finished:

        st.warning("받아쓰기 활동이 종료되었습니다.")

        if revealed:

            st.success("🏆 결과가 공개되었습니다!")

            with data["lock"]:
                passage = data["passage"]
                answers = dict(data["answers"])

            results = []

            for i in range(1, 8):

                group = f"Group {i}"
                answer = answers.get(group, "")

                correct, total, accuracy, details, errors = (
                    calculate_score(passage, answer)
                )

                results.append({
                    "group": group,
                    "accuracy": accuracy,
                    "correct": correct,
                    "total": total
                })

            results.sort(
                key=lambda x: x["accuracy"],
                reverse=True
            )

            for rank, result in enumerate(results, 1):

                st.subheader(
                    f"{rank}위 | {result['group']}"
                )

                st.metric(
                    "정확성",
                    f"{result['accuracy']}%"
                )

                st.progress(result["accuracy"] / 100)

        st.stop()

    # 모둠 선택
    group_names = [f"Group {i}" for i in range(1, 8)]

    selected_group = st.selectbox(
        "우리 모둠을 선택하세요.",
        group_names,
        key="selected_group"
    )

    st.info(
        "모둠을 선택한 뒤 받아쓰기 내용을 입력하세요. "
        "제출 후에도 활동 종료 전까지 수정할 수 있습니다."
    )

    # 모둠별 독립 입력창
    with data["lock"]:
        saved_answer = data["answers"].get(selected_group, "")

    widget_key = f"answer_{selected_group}"

    if widget_key not in st.session_state:
        st.session_state[widget_key] = saved_answer

    with st.form(f"form_{selected_group}"):

        answer = st.text_area(
            "Dictation Answer",
            height=300,
            placeholder="Write your answer here...",
            key=widget_key
        )

        submitted = st.form_submit_button(
            "답안 제출하기",
            type="primary",
            use_container_width=True
        )

    if submitted:

        with data["lock"]:

            if data["finished"]:
                st.error("활동이 종료되었습니다.")

            else:
                data["answers"][selected_group] = answer
                st.success(
                    f"{selected_group} 답안이 제출되었습니다!"
                )

    with data["lock"]:
        current_answer = data["answers"].get(selected_group, "")

    if current_answer.strip():
        st.success("현재 제출된 답안이 있습니다.")
    else:
        st.caption("아직 제출된 답안이 없습니다.")


# =====================================
# 7. 교사용
# =====================================

elif mode == "교사용":

    # 로그인
    if not st.session_state.get("teacher_authenticated", False):

        st.header("🔐 Teacher Login")

        password = st.text_input(
            "교사 비밀번호",
            type="password"
        )

        if st.button("로그인", type="primary"):

            if password == TEACHER_PASSWORD:
                st.session_state.teacher_authenticated = True
                st.rerun()

            else:
                st.error("비밀번호가 틀렸습니다.")

        st.stop()

    st.header("👩‍🏫 Teacher Dashboard")

    with data["lock"]:
        finished = data["finished"]
        revealed = data["revealed"]
        passage = data["passage"]
        answers = dict(data["answers"])

    # ---------------------------------
    # 지문 설정
    # ---------------------------------

    st.subheader("1. 정답 원문 설정")

    with st.form("passage_form"):

        new_passage = st.text_area(
            "정답 원문 (학생에게 공개되지 않습니다.)",
            value=passage,
            height=250,
            disabled=finished
        )

        save_passage = st.form_submit_button(
            "원문 저장",
            disabled=finished
        )

    if save_passage:

        with data["lock"]:
            data["passage"] = new_passage

        st.success("원문이 저장되었습니다.")
        st.rerun()

    st.divider()

    # ---------------------------------
    # 제출 현황
    # ---------------------------------

    st.subheader("2. 모둠별 제출 현황")

    if st.button("🔄 제출 현황 새로고침"):
        st.rerun()

    submitted_count = 0

    with data["lock"]:
        answers = dict(data["answers"])

    for i in range(1, 8):

        group = f"Group {i}"
        answer = answers.get(group, "")

        if answer.strip():
            submitted_count += 1
            st.write(f"**{group}** — ✅ 제출 완료")
        else:
            st.write(f"**{group}** — ⏳ 대기 중")

    st.write(f"제출 현황: {submitted_count} / 7")

    st.progress(submitted_count / 7)

    st.divider()

    # ---------------------------------
    # 활동 제어
    # ---------------------------------

    st.subheader("3. 활동 제어")

    if not finished:

        if st.button(
            "활동 종료",
            type="primary",
            use_container_width=True
        ):

            with data["lock"]:
                data["finished"] = True

            st.rerun()

    else:

        st.warning("활동이 종료되었습니다.")

        if not revealed:

            if st.button(
                "🏆 결과 공개하기",
                type="primary",
                use_container_width=True
            ):

                with data["lock"]:
                    data["revealed"] = True

                st.rerun()

        else:
            st.success("결과가 공개되었습니다.")

    # ---------------------------------
    # 결과
    # ---------------------------------

    if revealed:

        st.divider()
        st.subheader("4. Final Results")

        with data["lock"]:
            passage = data["passage"]
            answers = dict(data["answers"])

        results = []

        for i in range(1, 8):

            group = f"Group {i}"
            answer = answers.get(group, "")

            correct, total, accuracy, details, errors = (
                calculate_score(passage, answer)
            )

            results.append({
                "group": group,
                "correct": correct,
                "total": total,
                "accuracy": accuracy,
                "errors": errors,
                "details": details
            })

        results.sort(
            key=lambda x: x["accuracy"],
            reverse=True
        )

        st.subheader("🏆 Leaderboard")

        for rank, result in enumerate(results, 1):

            st.markdown(
                f"### {rank}위 — {result['group']}"
            )

            st.metric(
                "정확성",
                f"{result['accuracy']}%"
            )

            st.caption(
                f"정답 단어 {result['correct']}개 · "
                f"오류 {result['errors']}개"
            )

            st.progress(result["accuracy"] / 100)

        st.divider()

        st.subheader("Word-by-word Feedback")

        for result in results:

            with st.expander(result["group"]):

                for item in result["details"]:

                    if item["status"] == "correct":
                        st.success(
                            f"✓ {item['original']}"
                        )

                    elif item["status"] == "incorrect":
                        st.error(
                            f"✗ 정답: {item['original']} | "
                            f"입력: {item['answer']}"
                        )

                    elif item["status"] == "missing":
                        st.warning(
                            f"△ 누락: {item['original']}"
                        )

                    elif item["status"] == "extra":
                        st.error(
                            f"+ 추가: {item['answer']}"
                        )

        # CSV 다운로드
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)

        writer.writerow([
            "Group",
            "Correct Words",
            "Total Words",
            "Accuracy",
            "Errors"
        ])

        for result in results:

            writer.writerow([
                result["group"],
                result["correct"],
                result["total"],
                result["accuracy"],
                result["errors"]
            ])

        st.download_button(
            "📥 결과 CSV 다운로드",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name="dictation_results.csv",
            mime="text/csv"
        )

    # ---------------------------------
    # 새 활동 초기화
    # ---------------------------------

    st.divider()

    with st.expander("새 활동 시작"):

        st.warning(
            "초기화하면 모든 모둠의 답안과 활동 상태가 삭제됩니다."
        )

        confirm_reset = st.checkbox(
            "초기화에 동의합니다."
        )

        if st.button(
            "새 활동 초기화",
            disabled=not confirm_reset
        ):

            with data["lock"]:

                data["answers"] = {
                    f"Group {i}": "" for i in range(1, 8)
                }

                data["finished"] = False
                data["revealed"] = False

            st.success("초기화 완료!")
            st.rerun()


st.divider()

st.caption(
    "Group Dictation Challenge | Powered by Streamlit"
)
