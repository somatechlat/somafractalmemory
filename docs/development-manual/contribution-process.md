# Contribution Process

1. **Discuss** the change in `#somafractalmemory-dev` or open a GitHub issue.
2. **Branch** from `soma_integration` using the naming scheme `feature/<short-description>`.
3. **Implement** the change following the coding standards. Do not add new endpoints unless they align with the `/memories` manifesto.
4. **Update documentation** within the appropriate manual. The docs tree must remain compliant with the template: no stray files or directories.
5. **Run checks**:
   ```bash
   make lint test
   mkdocs build
   ```
6. **Open a Pull Request** with:
   - Linked issue or rationale.
   - Summary of changes.
   - Testing evidence (CLI dumps, curl scripts, or failing tests fixed).
7. **Review**: At least one maintainer must approve. Reviewers confirm:
   - `/memories` contract untouched or properly versioned.
   - No legacy references to `/store`, `/recall`, or graph APIs remain.
   - Documentation updated.
8. **Merge** using Squash & Merge. Delete the branch after merge.
