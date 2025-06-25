# Garlic Backend

📦 FastAPI 기반 지역 가게 등록 서비스 백엔드

---

## 🛠️ 설치한 주요 모듈

FastAPI 기반 웹 서버를 구동하기 위해 다음 Python 패키지들을 설치하였습니다:

| 패키지 이름           | 설명 |
|------------------------|------|
| `fastapi`              | 웹 프레임워크 |
| `uvicorn`              | ASGI 서버 (개발용 핫 리로딩 포함) |
| `python-multipart`     | HTML Form 데이터 처리용 (FastAPI의 Form 사용 시 필수) |
| `jinja2`               | 템플릿 렌더링 엔진 |
| `pydantic`             | 데이터 검증 및 유효성 검사 (Form 검증에 사용) |
| `aiofiles` *(선택)*    | 파일 업로드가 필요한 경우 사용할 수 있음 |
| `httpx` *(선택)*       | 비동기 HTTP 요청 (필요 시) |
| `starlette` *(fastapi에 포함)* | FastAPI 내부 기반 프레임워크 |

### 설치 명령어
```bash
pip install fastapi uvicorn python-multipart jinja2
