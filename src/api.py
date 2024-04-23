import os

from fastapi.params import Query
from starlette.responses import HTMLResponse

from src import service
from src.generators import html_generator
from fastapi import FastAPI
from pydantic import BaseModel
from celery.result import AsyncResult

app = FastAPI()
format_html = False


class TaskOut(BaseModel):
    id: str
    status: str
    result: str | None = None
    status_callback_url: str | None = None


# Sample url: https://tmt.org/?test-url=https://github.com/teemtee/tmt&test-name=/tests/core/smoke
# or for plans: https://tmt.org/?plan-url=https://github.com/teemtee/tmt&plan-name=/plans/features/basic
@app.get("/")
def find_test(
        test_url: str = Query(None, alias="test-url"),
        test_name: str = Query(None, alias="test-name"),
        test_ref: str = Query("default", alias="test-ref"),
        plan_url: str = Query(None, alias="plan-url"),
        plan_name: str = Query(None, alias="plan-name"),
        plan_ref: str = Query("default", alias="plan-ref"),
        out_format: str = Query("json", alias="format")
):
    # Parameter validations
    if (test_url is None and test_name is not None) or (test_url is not None and test_name is None):
        return "Invalid arguments!"
    if (plan_url is None and plan_name is not None) or (plan_url is not None and plan_name is None):
        return "Invalid arguments!"
    if plan_url is None and plan_name is None and test_url is None and test_name is None:
        return "Missing arguments!"
    # Disable Celery if not needed
    if os.environ.get("USE_CELERY") == "false":
        html_page = service.main(test_url, test_name, test_ref, plan_url, plan_name, plan_ref, out_format)
        return html_page
    r = service.main.delay(test_url, test_name, test_ref, plan_url, plan_name, plan_ref, out_format)
    # Special handling of response if the format is html
    if out_format == "html":
        global format_html
        format_html = True
        status_callback_url = f'{os.getenv("API_HOSTNAME")}/status?task-id={r.task_id}&html=true'
        return HTMLResponse(content=html_generator.generate_status_callback(r, status_callback_url))
    else:
        format_html = False  # To set it back to False after a html format request
        return _to_task_out(r)


@app.get("/status")
def status(task_id: str = Query(None, alias="task-id"),
           html: str = Query("false")) -> TaskOut | HTMLResponse:
    r = service.main.app.AsyncResult(task_id)
    if html == "true":
        status_callback_url = f'{os.getenv("API_HOSTNAME")}/status?task-id={r.task_id}&html=true'
        return HTMLResponse(content=html_generator.generate_status_callback(r, status_callback_url))
    return _to_task_out(r)


def _to_task_out(r: AsyncResult) -> TaskOut | str:
    return TaskOut(
        id=r.task_id,
        status=r.status,
        result=r.traceback if r.failed() else r.result,
        status_callback_url=f'{os.getenv("API_HOSTNAME")}/status?task-id={r.task_id}'
    )