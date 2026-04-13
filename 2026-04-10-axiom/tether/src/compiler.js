import fs from 'fs';
import path from 'path';

function walkSync(dir, filelist = []) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (e) {
        return filelist;
    }

    for (const file of files) {
        if (file === 'node_modules' || file === '.git' || file === '.tetherrules') continue;
        const filepath = path.join(dir, file);
        try {
            if (fs.statSync(filepath).isDirectory()) {
                filelist = walkSync(filepath, filelist);
            } else {
                filelist.push(filepath);
            }
        } catch (e) {
            // Ignore unreadable files
        }
    }
    return filelist;
}

export function compileContext() {
    let contextBundle = '';
    const files = walkSync('./');
    for (const file of files) {
        try {
            const stats = fs.statSync(file);
            if (stats.size > 100 * 1024) continue; // skip files > 100KB
            const content = fs.readFileSync(file, 'utf8');
            // Basic binary check
            if (content.indexOf('\0') === -1) {
                contextBundle += `--- FILE: ${file} ---\n${content}\n`;
            }
        } catch (err) {
            console.error(`Compiler error: ${err.message}`);
        }
    }
    console.log(`Compiled ${contextBundle.length} bytes of context.`);
    return contextBundle;
}
