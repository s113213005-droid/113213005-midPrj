from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from psycopg import AsyncConnection

from app.db import lifespan, getDB


templates = Jinja2Templates(directory="templates")

app = FastAPI(
    title="線上投稿與稿件審查系統",
    lifespan=lifespan
)

app.mount("/www", StaticFiles(directory="www"), name="www")


# / ->選擇作者/編輯
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

# 作者投稿列表
@app.get("/author/submissions")
async def submission_list(
    request: Request,
    conn: AsyncConnection = Depends(getDB)
):

    cur = await conn.execute("""
        SELECT s.id, s.category, s.title, s.status
        FROM submissions AS s
        JOIN users AS u ON s.author_id = u.id
        WHERE u.username = %s
        ORDER BY s.id DESC
    """, ("demo",))

    data = await cur.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="author_list.html",
        context={"submissions": data}
    )


# 新增投稿表單
@app.get("/author/submissions/new")
async def submission_new(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="submission_form.html",
        context={}
    )


# 接收表單並新增投稿
@app.post("/author/submissions/new")
async def submission_insert(
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    conn: AsyncConnection = Depends(getDB)
):

    await conn.execute("""
        INSERT INTO submissions
            (author_id, category, title, content)
        SELECT id, %s, %s, %s
        FROM users WHERE username = %s
    """, (
        category,
        title,
        content,
        "demo"
    ))

    return RedirectResponse(
        url="/author/submissions",
        status_code=303
    )

# 修改投稿
@app.get("/author/submissions/edit/{submission_id}")
async def submission_edit(
    submission_id: int,
    request: Request,
    db: AsyncConnection = Depends(getDB)
):

    cur = await db.execute("""
        SELECT s.id, s.category, s.title, s.content
        FROM submissions AS s
        JOIN users AS u ON s.author_id = u.id
        WHERE s.id = %s
          AND u.username = %s
          AND s.status = '編輯中'
    """, (submission_id, "demo"))

    data = await cur.fetchone()

    if data is None:
        return HTMLResponse("找不到投稿，或此投稿目前不能修改", status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="submission_edit.html",
        context={"data": data}
    )


# 接收修改資料
@app.post("/author/submissions/edit/{submission_id}")
async def submission_update(
    submission_id: int,
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    db: AsyncConnection = Depends(getDB)
):

    cur = await db.execute("""
        UPDATE submissions
        SET category = %s,
            title = %s,
            content = %s
        WHERE id = %s
          AND author_id = (
              SELECT id FROM users WHERE username = %s
          )
          AND status = '編輯中'
    """, (
        category,
        title,
        content,
        submission_id,
        "demo"
    ))

    if cur.rowcount == 0:
        return HTMLResponse("找不到投稿，或此投稿目前不能修改", status_code=404)

    return RedirectResponse(
        url="/author/submissions",
        status_code=303
    )


# 刪除投稿
@app.post("/author/submissions/delete/{submission_id}")
async def submission_delete(submission_id: int,db= Depends(getDB)):

    cur = await db.execute("""
        DELETE FROM submissions
        WHERE id = %s
          AND author_id = (
              SELECT id FROM users WHERE username = %s
          )
          AND status = '編輯中'
    """, (submission_id, "demo"))

    if cur.rowcount == 0:
        return HTMLResponse("找不到投稿，或此投稿目前不能刪除", status_code=404)

    return RedirectResponse(
        url="/author/submissions",
        status_code=303
    )
# 送出審查
@app.post("/author/submissions/submit/{submission_id}")
async def submission_submit(submission_id: int,db= Depends(getDB)):
    cur = await db.execute("""
        UPDATE submissions
        SET status = '審查中'
        WHERE id = %s
          AND author_id = (
              SELECT id FROM users WHERE username = %s
          )
          AND status = '編輯中'
    """, (submission_id, "demo"))

    # 確認是否成功更新資料
    if cur.rowcount == 0:
        return HTMLResponse(
            "找不到投稿，或此投稿目前不能送出審查",
            status_code=404
        )

    return RedirectResponse(
        url="/author/submissions",
        status_code=303
    )
    
#-------------編輯-------------#
# 待審查投稿清單
@app.get("/editor/submissions")
async def editor_list(
    request: Request,
    db: AsyncConnection = Depends(getDB)
):
    cur = await db.execute("""
        SELECT
            s.id,
            u.username AS author,
            s.category,
            s.title
        FROM submissions AS s
        JOIN users AS u ON s.author_id = u.id
        WHERE s.status = '審查中'
        ORDER BY s.id DESC
    """)

    data = await cur.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="editor_list.html",
        context={"submissions": data}
    )


# 查看投稿內容
@app.get("/editor/submissions/{submission_id}")
async def editor_detail(
    submission_id: int,
    request: Request,
    db: AsyncConnection = Depends(getDB)
):
    cur = await db.execute("""
        SELECT
            s.id,
            u.username AS author,
            s.category,
            s.title,
            s.content
        FROM submissions AS s
        JOIN users AS u ON s.author_id = u.id
        WHERE s.id = %s
          AND s.status = '審查中'
    """, (submission_id,))

    data = await cur.fetchone()

    if data is None:
        return HTMLResponse(
            "找不到投稿，或此投稿已經不在審查中",
            status_code=404
        )

    return templates.TemplateResponse(
        request=request,
        name="editor_detail.html",
        context={"data": data}
    )


# 通過投稿
@app.post("/editor/submissions/{submission_id}/approve")
async def editor_approve(
    submission_id: int,
    db: AsyncConnection = Depends(getDB)
):
    cur = await db.execute("""
        UPDATE submissions
        SET status = '已通過'
        WHERE id = %s
          AND status = '審查中'
    """, (submission_id,))

    if cur.rowcount == 0:
        return HTMLResponse(
            "找不到投稿，或此投稿已經不在審查中",
            status_code=404
        )

    return RedirectResponse(
        url="/editor/submissions",
        status_code=303
    )


# 退回投稿
@app.post("/editor/submissions/{submission_id}/reject")
async def editor_reject(
    submission_id: int,
    db: AsyncConnection = Depends(getDB)
):
    cur = await db.execute("""
        UPDATE submissions
        SET status = '編輯中'
        WHERE id = %s
          AND status = '審查中'
    """, (submission_id,))

    if cur.rowcount == 0:
        return HTMLResponse(
            "找不到投稿，或此投稿已經不在審查中",
            status_code=404
        )

    return RedirectResponse(
        url="/editor/submissions",
        status_code=303
    )