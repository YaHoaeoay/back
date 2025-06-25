from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, HttpUrl
from firebase_config import db
from passlib.hash import bcrypt
import re


app = FastAPI()
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
    google_map_url : HttpUrl = Field(..., description="구글 지도 링크")
    product : str = Field(..., description="가게 대표 상품")

    @field_validator('location')
    @classmethod
    def validate_location(cls, v):
        # "경상북도 의성군"으로 시작하고, 그 다음에 "**면"이 포함되어야 함
        if not re.match(r'^경상북도 의성군\s.+면', v):
            raise ValueError('주소는 "경상북도 의성군 **면 ..." 형식이어야 합니다.')
        return v

    @field_validator('google_map_url')
    @classmethod
    def validate_google_map_url(cls, v: HttpUrl):
        # 구글 맵 URL인지 확인
        if not ("google.com" in v.host or "goo.gl" in v.host):
            raise ValueError("구글 지도 링크여야 합니다 (예: https://www.google.com/maps/...)")
        return v


@app.get("/store/form")
def store_form(request: Request):
    return templates.TemplateResponse("store_form.html", {"request" : request})

@app.post("/store/submit")
def submit_store(
    request : Request,
    name : str = Form(..., description="가게 이름"),
    introduce : str = Form(..., max_length=1000, description="가게를 소개하는 글 (최소 30자 이상)"),
    location : str = Form(..., description="가게 위치 ('경상북도 의성군 **면 ...' 형식으로 작성해주세요.)"),
    google_map_url : HttpUrl = Form(..., description="구글 지도 링크"),
    product : str = Form(..., description="가게 대표 상품") 
):
    try:
        store = Store(
            name = name,
            introduce = introduce,
            location = location,
            google_map_url = google_map_url,
            product = product
        )
    except Exception as e:
        return templates.TemplateResponse("store_form.html", {
            "request" : request,
            "error" : str(e),
            "old" : {
                "name" : name,
                "introduce" : introduce,
                "location" : location,
                "google_map_url" : google_map_url,
                "product" : product
            }
        })
    
    try:
        db.collection("stores").add(store.model_dump(mode="json"))
    except Exception as e:
        return templates.TemplateResponse("store_form.html", {
            "request": request,
            "error": f"Firestore 저장 오류: {str(e)}",
            "old": store.model_dump()
        })

    return templates.TemplateResponse("store_detail.html", {"request" : request, "store" : store})


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

    hashed_pw = bcrypt.hash(password)

    db.collection("users").add({
        "name": name,
        "nickname": nickname,
        "id": id,
        "password": hashed_pw,
        "birthday": birthday + "******",  # 뒤는 마스킹
        "phone_number": phone_number
    })

    return RedirectResponse("/", status_code=302)





