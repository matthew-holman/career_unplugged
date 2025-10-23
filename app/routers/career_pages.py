from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.db.db import get_db
from app.models.career_page import CareerPageCreate, CareerPageRead
from app.handlers.career_page import CareerPageHandler

router = APIRouter(prefix="/career-pages", tags=["career-pages"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CareerPageRead)
def create_career_page(page: CareerPageCreate, db_session: Session = Depends(get_db)):
    handler = CareerPageHandler(db_session)
    return handler.create(page)


@router.get("/", status_code=status.HTTP_200_OK, response_model=list[CareerPageRead])
def list_career_pages(db_session: Session = Depends(get_db)):
    handler = CareerPageHandler(db_session)
    return handler.list_all()


@router.get("/{page_id}", status_code=status.HTTP_200_OK, response_model=CareerPageRead)
def get_career_page(page_id: int, db_session: Session = Depends(get_db)):
    handler = CareerPageHandler(db_session)
    page = handler.get(page_id)
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career page not found")
    return page


@router.put("/{page_id}", status_code=status.HTTP_200_OK, response_model=CareerPageRead)
def update_career_page(page_id: int, page_update: CareerPageCreate, db_session: Session = Depends(get_db)):
    handler = CareerPageHandler(db_session)
    updated = handler.update(page_id, page_update)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career page not found")
    return updated