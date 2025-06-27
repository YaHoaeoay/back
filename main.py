from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, HttpUrl
from firebase_config import db
from passlib.hash import bcrypt
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import re


app = FastAPI()

# 로그인 체크용 미들웨어 정의
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        protected_paths = ["/profile", "/store/form"]  # 로그인 필요 경로

        if request.url.path in protected_paths:
            user_id = request.cookies.get("user_id")
            if not user_id:
                return RedirectResponse("/login", status_code=302)

        response = await call_next(request)
        return response

# 미들웨어 등록
app.add_middleware(AuthMiddleware)

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return '홈화면입니다!'

class Store(BaseModel):
    name : str = Field(..., description="가게 이름")
    introduce : str = Field(..., max_length=1000, description="가게를 소개하는 글 (최소 30자 이상)")
    location : str = Field(..., description="가게 위치")
    # google_map_url : HttpUrl = Field(..., description="구글 지도 링크")
    # product : str = Field(..., description="가게 대표 상품")

    @field_validator('location')
    @classmethod
    def validate_location(cls, v):
        # "경상북도 의성군"으로 시작하고, 그 다음에 "**면"이 포함되어야 함
        if not re.match(r'^경상북도 의성군\s.+면', v):
            raise ValueError('주소는 "경상북도 의성군 **면 ..." 형식이어야 합니다.')
        return v

    # @field_validator('google_map_url')
    # @classmethod
    # def validate_google_map_url(cls, v: HttpUrl):
    #     # 구글 맵 URL인지 확인
    #     if not ("google.com" in v.host or "goo.gl" in v.host):
    #         raise ValueError("구글 지도 링크여야 합니다 (예: https://www.google.com/maps/...)")
    #     return v


@app.get("/store/form")
def store_form(request: Request):
    return templates.TemplateResponse("store_form.html", {"request" : request})

@app.post("/store/submit")
def submit_store(
    request : Request,
    name : str = Form(..., description="가게 이름"),
    introduce : str = Form(..., max_length=1000, description="가게를 소개하는 글 (최소 30자 이상)"),
    location : str = Form(..., description="가게 위치 ('경상북도 의성군 **면 ...' 형식으로 작성해주세요.)"),
    # google_map_url : HttpUrl = Form(..., description="구글 지도 링크"),
    # product : str = Form(..., description="가게 대표 상품") 
):
    try:
        store = Store(
            name = name,
            introduce = introduce,
            location = location,
            # google_map_url = google_map_url,
            # product = product
        )
    except Exception as e:
        return templates.TemplateResponse("store_form.html", {
            "request" : request,
            "error" : str(e),
            "old" : {
                "name" : name,
                "introduce" : introduce,
                "location" : location,
                # "google_map_url" : google_map_url,
                # "product" : product
            }
        })
    
    try:
        user_id = request.cookies.get("user_id")
        db.collection("stores").add({
            **store.model_dump(mode="json"),
            "user_id": user_id
        })

        # 작성자 닉네임 불러오기
        user_docs = db.collection("users").where("id", "==", user_id).get()
        nickname = user_docs[0].to_dict().get("nickname", "알 수 없음") if user_docs else "알 수 없음"

    except Exception as e:
        return templates.TemplateResponse("store_form.html", {
            "request": request,
            "error": f"Firestore 저장 오류: {str(e)}",
            "old": store.model_dump()
        })

    return templates.TemplateResponse("store_detail.html", {
        "request": request,
        "store": store,
        "nickname": nickname  # ✨ 추가됨
    })


# 회원가입
@app.get("/signup")
def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup")
async def signup(
    request: Request, 
    name: str = Form(...),
    nickname: str = Form(...),
    id: str = Form(...), 
    password: str = Form(...),
    password_check: str = Form(...),
    birthday: str = Form(...),
    phone_number: str = Form(...)
    ):

    form_data = await request.form()

    # 비밀번호 일치 확인
    if password != password_check:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "비밀번호가 일치하지 않습니다.",
            "old": form_data
        })


    # 주민번호 앞자리 형식 검사: YYMMDD-X
    if not re.match(r"^\d{6}-\d{1}$", birthday):
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "생년월일 형식이 올바르지 않습니다. 예: 990101-1",
            "old": form_data
        })

    # 전화번호 형식 검사: 000-0000-0000
    if not re.match(r"^\d{3}-\d{4}-\d{4}$", phone_number):
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "전화번호 형식이 올바르지 않습니다. 예: 010-1234-5678",
            "old": form_data
        })

    # 닉네임 중복 검사
    user_ref = db.collection("users").where("nickname", "==", nickname).get()
    if user_ref:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "이미 가입된 닉네임입니다.",
            "old": form_data
        })
    
    # 아이디 중복 검사
    user_ref = db.collection("users").where("id", "==", id).get()
    if user_ref:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "이미 가입된 아이디입니다.",
            "old": form_data
        })

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_pw = pwd_context.hash(password)

    db.collection("users").add({
        "name": name,
        "nickname": nickname,
        "id": id,
        "password": hashed_pw,
        "birthday": birthday + "******",  # 뒤는 마스킹
        "phone_number": phone_number
    })

    return RedirectResponse("/login", status_code=302)



# 로그인
@app.get("/login")
def login_form(request: Request):
    user_id = request.cookies.get("user_id")
    if user_id:
        # 이미 로그인 되어 있으면 홈으로
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(
    request: Request, 
    id: str = Form(...), 
    password: str = Form(...)
    ):

    users = db.collection("users").where("id", "==", id).get()
    if not users:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "존재하지 않는 아이디입니다."
        })

    user_data = users[0].to_dict()
    if not bcrypt.verify(password, user_data["password"]):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "비밀번호가 일치하지 않습니다."
        })

    # 로그인 성공 → 세션 쿠키 설정
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(key="user_id", value=id)
    return response


# 로그아웃
@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("user_id")
    return response



# 로그인 상태 확인
@app.get("/profile")
def profile(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    users = db.collection("users").where("id", "==", user_id).get()
    if not users:
        return RedirectResponse("/login", status_code=302)

    user_data = users[0].to_dict()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "id": user_id,
        "user": user_data  # <- signup에 유저 정보 전달
    })


@app.get("/api/profile")
def get_profile(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not logged in"})

    users = db.collection("users").where("id", "==", user_id).get()
    if not users:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    user_data = users[0].to_dict()
    return JSONResponse(content={"nickname": user_data["nickname"]})


@app.get("/my-posts")
def my_posts(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user_docs = db.collection("users").where("id", "==", user_id).get()
    if not user_docs:
        return RedirectResponse("/login", status_code=302)
    user_data = user_docs[0].to_dict()

    posts = db.collection("stores").where("user_id", "==", user_id).get()
    post_list = [doc.to_dict() for doc in posts]

    return templates.TemplateResponse("my_posts.html", {
        "request": request,
        "nickname": user_data.get("nickname", "사용자"),
        "posts": post_list
    })



