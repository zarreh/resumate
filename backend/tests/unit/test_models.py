"""Tests for SQLAlchemy models: instantiation, CRUD, relationships, JSONB, Vector."""

from datetime import UTC

from sqlalchemy import select

from src.models import (
    CareerHistoryEntry,
    CoverLetter,
    FeedbackLog,
    JobDescription,
    RefreshToken,
    ResumeTemplate,
    Session,
    SessionDecision,
    TailoredResume,
    User,
)


async def test_create_user(db_session):
    user = User(email="test@example.com", hashed_password="hashed", name="Test User")
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.created_at is not None
    assert user.updated_at is not None


async def test_query_user(db_session):
    user = User(email="query@example.com", hashed_password="h", name="Query")
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(
        select(User).where(User.email == "query@example.com")
    )
    fetched = result.scalar_one()
    assert fetched.name == "Query"
    assert fetched.id == user.id


async def test_create_refresh_token(db_session):
    from datetime import datetime

    user = User(email="token@example.com", hashed_password="h", name="Token")
    db_session.add(user)
    await db_session.flush()

    token = RefreshToken(
        user_id=user.id,
        token_hash="abc123hash",
        expires_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    db_session.add(token)
    await db_session.flush()

    assert token.id is not None
    assert token.user_id == user.id
    assert token.created_at is not None


async def test_career_entry_with_jsonb(db_session):
    user = User(email="career@example.com", hashed_password="h", name="Career")
    db_session.add(user)
    await db_session.flush()

    entry = CareerHistoryEntry(
        user_id=user.id,
        entry_type="work_experience",
        title="Software Engineer",
        organization="Acme Corp",
        bullet_points=["Built X", "Led Y"],
        tags=["python", "aws"],
        source="parsed_resume",
    )
    db_session.add(entry)
    await db_session.flush()

    result = await db_session.execute(
        select(CareerHistoryEntry).where(CareerHistoryEntry.id == entry.id)
    )
    fetched = result.scalar_one()
    assert fetched.bullet_points == ["Built X", "Led Y"]
    assert fetched.tags == ["python", "aws"]
    assert fetched.organization == "Acme Corp"


async def test_vector_column(db_session):
    user = User(email="vector@example.com", hashed_password="h", name="Vec")
    db_session.add(user)
    await db_session.flush()

    entry = CareerHistoryEntry(
        user_id=user.id,
        entry_type="work_experience",
        title="Engineer",
        bullet_points=[],
        tags=[],
        source="user_provided",
        embedding=[0.1] * 1536,
    )
    db_session.add(entry)
    await db_session.flush()

    result = await db_session.execute(
        select(CareerHistoryEntry).where(CareerHistoryEntry.id == entry.id)
    )
    fetched = result.scalar_one()
    assert len(fetched.embedding) == 1536


async def test_job_description(db_session):
    user = User(email="job@example.com", hashed_password="h", name="Job")
    db_session.add(user)
    await db_session.flush()

    jd = JobDescription(
        user_id=user.id,
        raw_text="We are looking for a software engineer...",
        analysis={"role_title": "Software Engineer", "required_skills": ["python"]},
    )
    db_session.add(jd)
    await db_session.flush()

    result = await db_session.execute(
        select(JobDescription).where(JobDescription.id == jd.id)
    )
    fetched = result.scalar_one()
    assert fetched.analysis["role_title"] == "Software Engineer"


async def test_session_with_relationships(db_session):
    user = User(email="session@example.com", hashed_password="h", name="Sess")
    db_session.add(user)
    await db_session.flush()

    jd = JobDescription(user_id=user.id, raw_text="JD text")
    db_session.add(jd)
    await db_session.flush()

    session = Session(
        user_id=user.id,
        job_description_id=jd.id,
        current_gate="analysis",
        selected_entry_ids=["entry-1", "entry-2"],
    )
    db_session.add(session)
    await db_session.flush()

    assert session.id is not None
    assert session.current_gate == "analysis"
    assert session.selected_entry_ids == ["entry-1", "entry-2"]


async def test_tailored_resume(db_session):
    user = User(email="resume@example.com", hashed_password="h", name="Res")
    db_session.add(user)
    await db_session.flush()

    jd = JobDescription(user_id=user.id, raw_text="JD")
    db_session.add(jd)
    await db_session.flush()

    session = Session(
        user_id=user.id,
        job_description_id=jd.id,
        selected_entry_ids=[],
    )
    db_session.add(session)
    await db_session.flush()

    resume = TailoredResume(
        session_id=session.id,
        user_id=user.id,
        content={"summary": "Experienced engineer", "sections": []},
        template_name="professional",
    )
    db_session.add(resume)
    await db_session.flush()

    assert resume.content["summary"] == "Experienced engineer"


async def test_resume_template(db_session):
    template = ResumeTemplate(
        name="professional",
        display_name="Professional",
        file_path="templates/latex/professional.tex.j2",
    )
    db_session.add(template)
    await db_session.flush()

    assert template.id is not None
    assert template.created_at is not None


async def test_feedback_log(db_session):
    user = User(email="feedback@example.com", hashed_password="h", name="FB")
    db_session.add(user)
    await db_session.flush()

    jd = JobDescription(user_id=user.id, raw_text="JD")
    db_session.add(jd)
    await db_session.flush()

    session = Session(
        user_id=user.id,
        job_description_id=jd.id,
        selected_entry_ids=[],
    )
    db_session.add(session)
    await db_session.flush()

    log = FeedbackLog(
        session_id=session.id,
        bullet_id="0_1",
        decision="rejected",
        feedback_text="Too vague",
    )
    db_session.add(log)
    await db_session.flush()

    assert log.id is not None
    assert log.decision == "rejected"


async def test_session_decision_with_vector(db_session):
    user = User(email="decision@example.com", hashed_password="h", name="Dec")
    db_session.add(user)
    await db_session.flush()

    jd = JobDescription(user_id=user.id, raw_text="JD")
    db_session.add(jd)
    await db_session.flush()

    session = Session(
        user_id=user.id,
        job_description_id=jd.id,
        selected_entry_ids=[],
    )
    db_session.add(session)
    await db_session.flush()

    decision = SessionDecision(
        session_id=session.id,
        user_id=user.id,
        decisions_snapshot={"approved": ["0_0"], "rejected": ["0_1"]},
        embedding=[0.5] * 1536,
    )
    db_session.add(decision)
    await db_session.flush()

    result = await db_session.execute(
        select(SessionDecision).where(SessionDecision.id == decision.id)
    )
    fetched = result.scalar_one()
    assert len(fetched.embedding) == 1536


async def test_cover_letter(db_session):
    user = User(email="cover@example.com", hashed_password="h", name="CL")
    db_session.add(user)
    await db_session.flush()

    jd = JobDescription(user_id=user.id, raw_text="JD")
    db_session.add(jd)
    await db_session.flush()

    session = Session(
        user_id=user.id,
        job_description_id=jd.id,
        selected_entry_ids=[],
    )
    db_session.add(session)
    await db_session.flush()

    cl = CoverLetter(
        session_id=session.id,
        user_id=user.id,
        content="Dear Hiring Manager...",
    )
    db_session.add(cl)
    await db_session.flush()

    assert cl.id is not None
    assert cl.content == "Dear Hiring Manager..."


async def test_cascade_delete_user(db_session):
    user = User(email="cascade@example.com", hashed_password="h", name="Cascade")
    db_session.add(user)
    await db_session.flush()

    entry = CareerHistoryEntry(
        user_id=user.id,
        entry_type="project",
        title="My Project",
        bullet_points=["Did stuff"],
        tags=["go"],
        source="user_provided",
    )
    db_session.add(entry)
    await db_session.flush()

    await db_session.delete(user)
    await db_session.flush()

    result = await db_session.execute(
        select(CareerHistoryEntry).where(CareerHistoryEntry.id == entry.id)
    )
    assert result.scalar_one_or_none() is None
