from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator, HttpUrl
from fastapi.middleware.cors import CORSMiddleware
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
    location : str = Form(..., description="가게 위치"),
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

    return templates.TemplateResponse("store_detail.html", {"request" : request, "store" : store})



