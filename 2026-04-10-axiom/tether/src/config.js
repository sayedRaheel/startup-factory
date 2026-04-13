import fs from 'fs';

export function loadConfig() {
    if (fs.existsSync('.tetherrules')) {
        const rules = fs.readFileSync('.tetherrules', 'utf8');
        return {
            strictMode: rules.includes('strict_mode = true')
        };
    }
    return { strictMode: false };
}
