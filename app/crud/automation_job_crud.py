from sqlalchemy.orm import Session

from app.models.automation_job import AutomationJob


def create_ocr_job(
    db: Session,
    user_id: int,
    project_id: int,
    document_id: int,
    prompt_id: int,
    ocr_result_id: int,
):
    payload = {
        "document_id": document_id,
        "prompt_id": prompt_id,
        "ocr_result_id": ocr_result_id,
    }

    job = AutomationJob(
        user_id=user_id,
        project_id=project_id,
        type="OCR_DOCUMENT",
        status="PENDING",
        payload_json=payload,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job