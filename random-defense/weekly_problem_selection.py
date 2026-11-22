import os
import re

from solvedac_api import (
    COMMON_EXCLUDED_TAGS,
    PROJECT_ROOT,
    SolvedAcError,
    load_credentials,
    select_boj_problems,
)


EXCLUDED_TAGS = COMMON_EXCLUDED_TAGS | {"math"}


def load_exclude_list(file_path):
    """파일에서 문제 번호들을 읽어 집합으로 반환한다."""
    if not file_path.exists():
        return set()
    return set(map(int, re.findall(r"\d+", file_path.read_text(encoding="utf-8"))))


def save_new_problems(file_path, new_problems):
    """새로 선택한 문제 번호들을 한 줄에 쉼표로 구분해 추가한다."""
    if not new_problems:
        return

    problems_str = ", ".join(map(str, sorted(new_problems)))
    with file_path.open("a", encoding="utf-8") as file:
        if file.tell() > 0:
            file.write("\n")
        file.write(problems_str)


def select_problems(credentials, tier, group_name, exclude_set):
    conditions = [(f"{tier}{level}", 200) for level in range(5, 0, -1)]
    conditions.extend([(tier, 200), (tier, 201)])
    selected = []
    for difficulty, solved_count in conditions:
        query = f"*{difficulty} s#{solved_count}.. %ko oj:boj"
        print(f"{group_name} [{query}] 검색 중", flush=True)
        candidates = select_boj_problems(credentials, query, EXCLUDED_TAGS, exclude_set, limit=1)
        if candidates:
            number = candidates[0]
            selected.append(number)
            print(f"선택된 문제: {number}", flush=True)
        else:
            print("조건에 맞는 미선정 문제를 찾지 못했습니다.", flush=True)
    return selected


def main():
    try:
        credentials = load_credentials()
        silver_path = PROJECT_ROOT / (os.getenv("EXCLUDE_SILVER_PATH") or "random-defense/exclude_silver.txt")
        gold_path = PROJECT_ROOT / (os.getenv("EXCLUDE_GOLD_PATH") or "random-defense/exclude_gold.txt")

        for path in (silver_path, gold_path):
            if not path.parent.is_dir():
                raise OSError(f"제외 목록 폴더를 찾을 수 없습니다: {path.parent}")
        exclude_silver = load_exclude_list(silver_path)
        exclude_gold = load_exclude_list(gold_path)
        silver_selected = select_problems(credentials, "s", "실버", exclude_silver)
        gold_selected = select_problems(credentials, "g", "골드", exclude_gold)

        print("\n=== 최종 선택 결과 ===")
        print(f"실버: {sorted(silver_selected)}")
        print(f"골드: {sorted(gold_selected)}")

        save_new_problems(silver_path, silver_selected)
        save_new_problems(gold_path, gold_selected)
        if silver_selected or gold_selected:
            print("제외 목록 파일이 업데이트되었습니다.")
    except SolvedAcError as error:
        print(f"오류: {error}")
        return 1
    except OSError as error:
        print(f"제외 목록을 처리하지 못했습니다: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
