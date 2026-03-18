#!/bin/bash

PROJECT_DIR="/Users/ashwinpasupathy/Documents/Claude Prism"
OUTPUT_FILE="$PROJECT_DIR/project_dump.txt"

# Delete old dump first
rm -f "$OUTPUT_FILE"

{
    echo "=== FILE TREE ==="
    find "$PROJECT_DIR" -type f \
        -not -path '*/.git/*' \
        -not -path '*/.claude/*' \
        -not -path '*/__pycache__/*' \
        -not -name 'project_dump.txt' \
        -not -name 'dump.sh' \
        | sort

    echo ""
    echo "=== FILE CONTENTS ==="

    find "$PROJECT_DIR" -type f \( \
        -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \
        -o -name "*.json" -o -name "*.md" -o -name "*.css" \
        -o -name "*.html" -o -name "*.yaml" -o -name "*.yml" \
        -o -name "*.py" -o -name "*.sql" -o -name "*.prisma" \
        -o -name "*.sh" -o -name "*.toml" -o -name "*.cfg" \
        -o -name "*.env.example" \
    \) \
        -not -path '*/.git/*' \
        -not -path '*/.claude/*' \
        -not -path '*/__pycache__/*' \
        -not -name 'project_dump.txt' \
        -not -name 'dump.sh' \
        | sort | while read -r file; do
            echo ""
            echo "=========================================="
            echo "FILE: $file"
            echo "=========================================="
            cat "$file"
        done

} > "$OUTPUT_FILE"

echo "Done! Output saved to: $OUTPUT_FILE"
echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo "Lines: $(wc -l < "$OUTPUT_FILE")"
