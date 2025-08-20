# KireMisu Development Context (Deprecated)

⚠️ **This file has been restructured for better developer experience**

## New Documentation Structure

### Core Files (Always Load)
- **`/docs/DEV_CONTEXT.md`** - Essential development context (50 lines vs 200+)
- **`/docs/SECURITY.md`** - Security checklist and patterns
- **`/docs/TESTING.md`** - Testing commands and patterns

### Reference Files (Load as Needed)
- **`/docs/API_PATTERNS.md`** - FastAPI patterns and examples
- **`/docs/UI_SYSTEM.md`** - Design system and components
- **`/docs/DEPLOYMENT.md`** - Docker and Kubernetes deployment
- **`/docs/examples/ui-mock.tsx`** - UI implementation reference

### Existing Files (Unchanged)
- **`kiremisu_prd.md`** - Product requirements and vision
- **`kiremisu_data_model.md`** - Database schema and design
- **`kiremisu_tech_stack.md`** - Technology decisions and architecture

## Migration Benefits
- ⚡ **50% faster context loading** - Essential info in focused files
- 🎯 **Task-specific documentation** - Only load what you need
- 🔒 **Security-first development** - Dedicated security checklist
- 🧪 **Integrated testing** - Clear testing commands and patterns
- 📖 **Better maintainability** - Single responsibility per document

## Quick Start
For new development sessions, start with:
1. `/docs/DEV_CONTEXT.md` - Core context and commands
2. Task-specific docs as needed
3. This restructure improves development velocity while maintaining completeness

---

*This migration was completed on 2025-08-16. Backup of original files available in `/docs/backup-[timestamp]/`*

- activate the local .venv before running any builds or tests