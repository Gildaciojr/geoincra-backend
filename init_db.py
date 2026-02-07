from app.core.database import Base, engine

# Importa TODOS os models para registrar no metadata
import app.models  # noqa: F401

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Banco inicializado com sucesso")
