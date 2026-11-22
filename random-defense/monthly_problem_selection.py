from solvedac_api import COMMON_EXCLUDED_TAGS, SolvedAcError, load_credentials, select_boj_problems


QUERIES = [
    f"*{tier}{level} s#150.. %ko oj:boj"
    for tier in ("s", "g")
    for level in range(5, 0, -1)
]


def main():
    credentials = load_credentials()
    results = {}

    for query in QUERIES:
        print(f"[{query}] 검색 중", flush=True)
        candidates = select_boj_problems(credentials, query, COMMON_EXCLUDED_TAGS, set(), limit=20)
        results[query] = [str(number) for number in candidates]

        print(f"[{query}] 상위 20개 문제 번호:")
        print(results[query])
        print("=" * 50)

    return results


if __name__ == "__main__":
    try:
        results = main()
    except SolvedAcError as error:
        print(f"오류: {error}")
        raise SystemExit(1) from None

    for tier, group_name in (("s", "실버"), ("g", "골드")):
        numbers = {
            number
            for query, candidates in results.items()
            if query.startswith(f"*{tier}")
            for number in candidates
        }
        print(f"{group_name} 문제 오름차순:")
        print(", ".join(sorted(numbers, key=int)))
