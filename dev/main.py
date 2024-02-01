from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
import uuid

DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # Async SQLite database
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

# Models
class Workflows(Base):
    __tablename__ = 'workflows'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    status = Column(String(30), default="Pending")
    done = Column(Integer, default=0)
    total = Column(Integer, default=1)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    def get_workflow(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "done": self.done,
            "total": self.total,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }

class WorkflowJobs(Base):
    __tablename__ = 'workflow_jobs'
    id = Column(Integer, primary_key=True)
    jobid = Column(Integer)
    wf_id = Column(Integer, ForeignKey('workflows.id'))
    status = Column(String(30), default="Running")
    # Define other fields as needed

# FastAPI app
app = FastAPI()

# Additional routes adapted to FastAPI
@app.get("/api/service-info")
async def get_service_info():
    return JSONResponse(content={'status': "running"})

# Dependency
async def get_db_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

@app.get("/api/workflows")
async def get_workflows(db: AsyncSession = Depends(get_db_session)):
    async with db:
        result = await db.execute(select(Workflows))
        workflows = result.scalars().all()
        workflows_data = [wf.get_workflow() for wf in workflows]
        return JSONResponse(content={'workflows': workflows_data, 'count': len(workflows_data)})


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Routes
@app.post("/workflows/")
async def create_workflow(db: AsyncSession = Depends(get_db_session)):
    new_workflow = Workflows(name=str(uuid.uuid4()), status="Running")
    db.add(new_workflow)
    await db.commit()
    await db.refresh(new_workflow)
    return new_workflow.get_workflow()

@app.get("/workflows/{workflow_id}")
async def read_workflow(workflow_id: int, db: AsyncSession = Depends(get_db_session)):
    async with db:
        result = await db.execute(select(Workflows).filter(Workflows.id == workflow_id))
        workflow = result.scalars().first()
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow.get_workflow()

@app.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: int, name: str, db: AsyncSession = Depends(get_db_session)):
    async with db:
        workflow = await db.get(Workflows, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow.name = name
        await db.commit()
        return workflow.get_workflow()

# Additional routes can be added following the same pattern.
