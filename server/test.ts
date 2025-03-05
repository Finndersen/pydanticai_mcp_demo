import { minimatch } from 'minimatch';
import path from "path";
import fs from "fs/promises";

function isGlobMatch(path: string, pattern: string): boolean {
    // const globPattern = pattern.includes('*') ? pattern : `**/${pattern}/**`;
    const match = minimatch(path, pattern, { dot: true });
    console.log(path, pattern, match);
    return match;
}

async function searchFiles(
    rootPath: string,
    pattern: string,
    excludePatterns: string[] = []
): Promise<string[]> {
    const results: string[] = [];

    async function search(currentPath: string) {
        const entries = await fs.readdir(currentPath, { withFileTypes: true });

        for (const entry of entries) {
            const fullPath = path.join(currentPath, entry.name);

            try {

                // Check if path matches any exclude pattern
                const relativePath = path.relative(rootPath, fullPath);
                const shouldExclude = excludePatterns.some(pattern =>
                    minimatch(relativePath, pattern, { dot: true })
                );

                if (shouldExclude) {
                    continue;
                }

                // Use glob matching for the search pattern as well
                if (minimatch(relativePath, pattern, { dot: true })) {
                    results.push(fullPath);
                }

                if (entry.isDirectory()) {
                    await search(fullPath);
                }
            } catch (error) {
                // Skip invalid paths during search
                continue;
            }
        }
    }

    await search(rootPath);
    return results;
}

isGlobMatch('src/filesystem/test.ts', 'test.ts');
isGlobMatch('src/filesystem/test.ts', 'test');
isGlobMatch('src/filesystem/__init__.py', '*__init__.py');
isGlobMatch('src/filesystem/__init__.py', '**__init__.py');
isGlobMatch('src/filesystem/__init__.py', '*/__init__.py');
isGlobMatch('src/filesystem/__init__.py', '**/__init__.py');
isGlobMatch('src/filesystem/__init__.py', '*.py');
isGlobMatch('src/filesystem/file.py', '*.py');
isGlobMatch('file.py', '*.py');
isGlobMatch('src/filesystem/file.py', '**/*.py');
isGlobMatch('src/filesystem/test.ts', 'filesystem/**');
isGlobMatch('src/filesystem/test.ts', 'src/**/test.ts');
isGlobMatch('.venv/', '**/.venv');
isGlobMatch('.venv/', '.venv');

console.log(await searchFiles('/Users/finn.andersen/projects/servers/', '**/*', ['.git', '**/node_modules', '.github']));