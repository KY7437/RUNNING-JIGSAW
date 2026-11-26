
import streamlit as st
import re
import csv
import io
from difflib import SequenceMatcher

# =====================================
# 1. 기본 설정
# =====================================

st.set_page_config(
    page_title="Group Dictation Challenge",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Group Dictation Challenge")
st.caption("Read, Remember, Reconstruct!")

# =====================================
# 2. 기본 지문
# =====================================

DEFAULT_PASSAGE = """A Fresh Start

On New Year’s Eve, Emily was cleaning her room when she discovered an old notebook under her desk. Inside, she found a list of New Year’s resolutions she had written a year earlier: exercise every morning, read thirty books, and improve her English.

However, she had given up on most of her goals before February. “Why did I fail to keep my promises?” she wondered. She realized that her goals had been too ambitious, and she had expected immediate results.

During dinner, Emily shared her concerns with her older brother. He listened carefully and said, “You don’t have to change your entire life overnight. Why don’t you start with something small?”

His advice inspired her to make a more realistic plan. Instead of exercising every morning, she would take a twenty-minute walk three times a week. Instead of reading thirty books, she would read ten pages a day. She also decided to keep an English diary every weekend.

Emily knew that following her new plan wouldn’t always be easy; there would be challenges, unexpected events, and moments when she wanted to give up. However, she promised herself that she would keep trying, even if she made mistakes.

As the clock struck midnight, Emily opened her notebook and wrote one final sentence: “This year, I don’t have to be perfect. I just have to be better than I was yesterday!”
"""

# =====================================
# 3. 단어 정규화
# =====================================

def normalize_word(word):
    word = word.replace("’", "'")
    return re.sub(r"[^\w'-]", "", word).casefold()


# =====================================
# 4. 채점 함수
# =====================================

def calculate_score(original, answer):

    original_words = original.split()
    answer_words = answer.split()

    original_norm = [
        normalize_word(w) for w in original_words
    ]

    answer_norm = [
        normalize_word(w) for w in answer_words
    ]

    matcher = SequenceMatcher(
        None,
        original_norm,
        answer_norm,
        autojunk=False
    )

    correct = 0
    details = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":

            for i, j in zip(range(i1, i2), range(j1, j2)):
                correct += 1

                details.append({
                    "status": "correct",
                    "original": original_words[i],
                    "answer": answer_words[j]
                })

        elif tag == "replace":

            original_part = original_words[i1:i2]
            answer_part = answer_words[j1:j2]

            paired = min(
                len(original_part),
                len(answer_part)
            )

            for i in range(paired):
                details.append({
                    "status": "incorrect",
                    "original": original_part[i],
                    "answer": answer_part[i]
                })

            for word in original_part[paired:]:
                details.append({
                    "status": "missing",
                    "original": word,
                    "answer": "(누락)"
                })

            for word in answer_part[paired:]:
                details.append({
                    "status": "extra",
                    "original": "(없음)",
                    "answer": word
                })

        elif tag == "delete":

            for word in original_words[i1:i2]:
                details.append({
                    "status": "missing",
                    "original": word,
                    "answer": "(누락)"
                })

        elif tag == "insert":

            for word in answer_words[j1:j2]:
                details.append({
                    "status": "extra",
                    "original": "(없음)",
                    "answer": word
                })

    total = max(
        len(original_words),
        len(answer_words),
        1
    )

    score = round(correct / total * 100, 1)

    return correct, total, score, details


# =====================================
# 5. 세션 초기화
# =====================================

if "passage" not in st.session_state:
    st.session_state.passage = DEFAULT_PASSAGE

if "group_count" not in st.session_state:
    st.session_state.group_count = 4

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "finished" not in st.session_state:
    st.session_state.finished = False

if "revealed" not in st.session_state:
    st.session_state.revealed = False


# =====================================
# 6. 교사 화면
# =====================================

st.sidebar.header("Teacher Menu")

menu = st.sidebar.radio(
    "Select a page",
    ["Activity Setup", "Group Answers", "Results"]
)

# -------------------------------------
# A. 활동 설정
# -------------------------------------

if menu == "Activity Setup":

    st.header("1. Activity Setup")

    st.subheader("Original Passage")

    passage = st.text_area(
        "교사용 원문",
        value=st.session_state.passage,
        height=350,
        disabled=st.session_state.finished
    )

    if not st.session_state.finished:
        if st.button("Save Passage"):
            st.session_state.passage = passage
            st.success("지문이 저장되었습니다.")

    st.divider()

    st.subheader("Group Settings")

    if not st.session_state.finished:

        group_count = st.number_input(
            "모둠 수",
            min_value=1,
            max_value=20,
            value=st.session_state.group_count,
            step=1
        )

        if st.button("Save Group Settings"):
            st.session_state.group_count = group_count

            for i in range(1, group_count + 1):
                st.session_state.answers.setdefault(
                    f"Group {i}", ""
                )

            st.success("모둠 설정이 저장되었습니다.")

    else:
        st.write(
            f"총 {st.session_state.group_count}개 모둠"
        )

    st.divider()

    st.subheader("Activity Control")

    if not st.session_state.finished:

        st.info("활동 진행 중 · 시간 제한 없음")

        if st.button(
            "Finish Activity",
            type="primary"
        ):
            st.session_state.passage = passage
            st.session_state.finished = True
            st.rerun()

    else:

        st.warning("활동이 종료되었습니다.")

        if not st.session_state.revealed:

            st.info("아직 결과가 공개되지 않았습니다.")

            if st.button(
                "Reveal Results",
                type="primary"
            ):
                st.session_state.revealed = True
                st.rerun()

        else:
            st.success("결과가 공개되었습니다!")

# -------------------------------------
# B. 모둠별 답안 입력
# -------------------------------------

elif menu == "Group Answers":

    st.header("2. Group Answers")

    if st.session_state.finished:

        st.warning("활동이 종료되어 답안을 수정할 수 없습니다.")

    else:

        st.info(
            "각 모둠의 답안을 교사가 취합하여 입력해 주세요."
        )

    for i in range(1, st.session_state.group_count + 1):

        group = f"Group {i}"

        if group not in st.session_state.answers:
            st.session_state.answers[group] = ""

        with st.expander(group, expanded=True):

            answer = st.text_area(
                f"{group} Answer",
                value=st.session_state.answers[group],
                height=180,
                key=f"input_{group}",
                disabled=st.session_state.finished
            )

            if not st.session_state.finished:
                if st.button(
                    f"Save {group}",
                    key=f"save_{group}"
                ):
                    st.session_state.answers[group] = answer
                    st.success("답안이 저장되었습니다.")

    if not st.session_state.finished:

        if st.button("Save All Answers"):

            for i in range(1, st.session_state.group_count + 1):
                group = f"Group {i}"
                key = f"input_{group}"

                st.session_state.answers[group] = (
                    st.session_state.get(key, "")
                )

            st.success("모든 답안이 저장되었습니다.")

# -------------------------------------
# C. 결과 화면
# -------------------------------------

elif menu == "Results":

    st.header("3. Results & Leaderboard")

    if not st.session_state.finished:

        st.warning("먼저 활동을 종료해 주세요.")

    elif not st.session_state.revealed:

        st.warning(
            "교사가 결과를 공개하기 전까지 "
            "점수를 확인할 수 없습니다."
        )

    else:

        results = []

        for i in range(1, st.session_state.group_count + 1):

            group = f"Group {i}"
            answer = st.session_state.answers.get(group, "")

            correct, total, score, details = calculate_score(
                st.session_state.passage,
                answer
            )

            results.append({
                "group": group,
                "correct": correct,
                "total": total,
                "score": score,
                "details": details
            })

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        st.subheader("🏆 Final Leaderboard")

        for rank, result in enumerate(results, 1):

            st.markdown(
                f"### {rank}. {result['group']}"
            )

            st.metric(
                "Score",
                f"{result['correct']} / {result['total']}",
                f"{result['score']}%"
            )

            st.progress(result["score"] / 100)

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

                    else:

                        st.error(
                            f"+ 추가 단어: {item['answer']}"
                        )

        # CSV 다운로드
        csv_buffer = io.StringIO()

        writer = csv.writer(csv_buffer)

        writer.writerow([
            "Group",
            "Correct Words",
            "Total Words",
            "Score"
        ])

        for result in results:
            writer.writerow([
                result["group"],
                result["correct"],
                result["total"],
                result["score"]
            ])

        st.download_button(
            "Download Results (CSV)",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name="dictation_results.csv",
            mime="text/csv"
        )


# =====================================
# 7. 하단 안내
# =====================================

st.divider()

st.caption(
    "Group Dictation Challenge | "
    "Created with Python and Streamlit"
)
