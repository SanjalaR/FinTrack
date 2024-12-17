from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import datetime as dt
import matplotlib.pyplot as plt
import io
import base64
from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DB_URL = 'sqlite:///./test.db'
Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ItemModel(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    date = Column(String)
    purpose = Column(String)
    category = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Item(BaseModel):
    amount: float
    date: str
    purpose: str
    category: str

categories = ['Food & Groceries', 'Entertainment', 'Healthcare', 'Transportation', 'Work/Education', 'Personal & Family', 'Other']
colors = ['#48684F', '#6e9074', '#475242', '#616e4d', '#2f3e36', '#344e37', '#2e3d2a']

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

@app.get('/', response_class=HTMLResponse)
async def home(req: Request, db: Session = Depends(get_db)):
    items = db.query(ItemModel).all()
    return templates.TemplateResponse('index.html', {'request': req, 'items': items})

@app.post('/add', response_class=HTMLResponse)
async def add(req: Request, amount: str = Form(...), purpose: str = Form(...), category: str = Form(...), db: Session = Depends(get_db)):
    item = ItemModel(amount=float(amount), date=dt.datetime.now().strftime("%d-%m-%Y, %H:%M:%S"), purpose=purpose, category=category)
    db.add(item)
    db.commit()
    items = db.query(ItemModel).all()
    return templates.TemplateResponse('index.html', {'request': req, 'items': items})

@app.get('/monthly', response_class=HTMLResponse)
async def monthly(req: Request, db: Session = Depends(get_db)):
    curr_month = dt.date.today().month
    tot_spending = 0
    cat_spending = {}

    items = db.query(ItemModel).all()
    for item in items:
        if dt.datetime.strptime(str(item.date), "%d-%m-%Y, %H:%M:%S").month == curr_month:
            tot_spending+=item.amount
            if item.category in list(cat_spending.keys()):
                cat_spending[str(item.category)]+=item.amount
            else:
                cat_spending[str(item.category)] = item.amount

    categories_list = list(cat_spending.keys())
    spending_list = list(cat_spending.values())
    fig = plt.figure(figsize=(5, 5))
    plt.pie(spending_list, labels=categories_list, colors=colors)
    plt.title("Monthly Expenses Breakdown")
    fig.set_facecolor("#ECDFCC")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close()
    return templates.TemplateResponse('review.html', {'request': req, 'total': tot_spending, 'cat_spending': cat_spending, 'img_data': img_data})
