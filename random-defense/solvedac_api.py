import json
import os
import re
import time
from itertools import count
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_URL = "https://solved.ac/api/v4/problems"
HTTP_TIMEOUT = 15
# 기하학, 물리학, 확률, 임의 정밀도 / 큰 수 연산, 애드 혹
COMMON_EXCLUDED_TAGS = frozenset({"geom", "physics", "prob", "big", "adhoc"})


class SolvedAcError(Exception):
    pass


def load_credentials():
    load_dotenv(PROJECT_ROOT / ".env")
    credentials = {
        "x-client-id": os.getenv("SOLVEDAC_CLIENT_ID", "").strip(),
        "x-client-secret": os.getenv("SOLVEDAC_CLIENT_SECRET", "").strip(),
    }
    if not all(credentials.values()):
        raise SolvedAcError(".env에 SOLVEDAC_CLIENT_ID와 SOLVEDAC_CLIENT_SECRET을 입력하세요.")
    return credentials


def fetch_problem_page(credentials, query, page, seed):
    params = urlencode({"q": query, "sort": "random", "page": page, "seed": seed})
    request = Request(
        f"{PROBLEMS_URL}?{params}",
        headers={"Accept": "application/json", "User-Agent": "algoriming-random-defense/1.0"},
    )
    for header, value in credentials.items():
        request.add_unredirected_header(header, value)

    for attempt in range(2):
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT) as response:
                return json.load(response)
        except HTTPError as error:
            with error:
                if error.headers.get("CF-Mitigated") == "challenge":
                    raise SolvedAcError("solved.ac API가 Cloudflare 접속 확인을 요청했습니다.") from None
                if error.code in (401, 403):
                    raise SolvedAcError(
                        f"solved.ac API 요청이 거부되었습니다 (HTTP {error.code}). "
                        "앱의 클라이언트 ID와 시크릿을 확인하세요."
                    ) from None
                if error.code != 429:
                    raise SolvedAcError(f"solved.ac API 요청에 실패했습니다 (HTTP {error.code}).") from None
                retry_after = error.headers.get("Retry-After", "")

            if attempt == 0 and re.fullmatch(r"[0-9]{1,2}", retry_after):
                delay = int(retry_after)
                if delay <= 30:
                    print(f"solved.ac API 호출 한도에 도달했습니다. {delay}초 후 다시 요청합니다.", flush=True)
                    time.sleep(delay)
                    continue
            raise SolvedAcError("solved.ac API 호출 한도에 도달했습니다 (HTTP 429). 잠시 후 실행하세요.") from None
        except OSError as error:
            raise SolvedAcError("solved.ac API에 연결하지 못했거나 응답 대기 시간이 초과되었습니다.") from error
        except ValueError as error:
            raise SolvedAcError("solved.ac API에서 JSON 응답을 받지 못했습니다.") from error


def select_boj_problems(credentials, query, excluded_tags, excluded_ids, limit):
    """백준 문제를 최대 limit개 선택하고 선택된 문제의 번호를 제외 집합에 추가한다."""
    selected = []
    # 같은 검색의 다음 페이지는 동일한 랜덤 시드를 사용한다.
    seed = uuid4().hex
    for page in count(1):
        response = fetch_problem_page(credentials, query, page, seed)
        for diagnostic in response.get("diagnostics", []):
            if diagnostic["severity"] == "error":
                raise SolvedAcError(f"검색 조건 오류 ({query}): {diagnostic['message']}")

        problems = response["problems"]
        for problem in problems:
            if any(tag["key"] in excluded_tags for tag in problem["tags"]):
                continue

            # 같은 문제가 여러 백준 번호로 등록된 경우 기존 번호도 모두 확인한다.
            boj_ids = [
                int(judge["problemId"])
                for judge in problem["judgeIds"]
                if judge["ojId"] == "boj" and re.fullmatch(r"[0-9]+", judge["problemId"])
            ]
            if boj_ids and excluded_ids.isdisjoint(boj_ids):
                selected.append(boj_ids[0])
                excluded_ids.update(boj_ids)
                if len(selected) == limit:
                    return selected

        if not problems or page * response["pageSize"] >= response["total"]:
            return selected
