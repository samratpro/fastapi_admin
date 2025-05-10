# # api/students.py
# from app.core.permission import has_permission

# @router.post("/")
# @has_permission("create")
# async def create_student(
#     student_in: StudentCreate,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_active_user)
# ):
#     # Your create logic here
#     pass
