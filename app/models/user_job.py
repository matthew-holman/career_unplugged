from sqlmodel import Field, SQLModel


class UserJobBase(SQLModel, table=False):  # type: ignore
    user_id: int = Field(nullable=False, foreign_key="user.id", index=True)
    job_id: int = Field(nullable=False, foreign_key="job.id", index=True)
    applied: bool = Field(nullable=False, default=False)
    ignored: bool = Field(nullable=False, default=False)


class UserJob(UserJobBase, table=True):  # type: ignore
    __tablename__ = "user_job"
    user_id: int = Field(
        nullable=False, foreign_key="user.id", index=True, primary_key=True
    )
    job_id: int = Field(
        nullable=False, foreign_key="job.id", index=True, primary_key=True
    )
