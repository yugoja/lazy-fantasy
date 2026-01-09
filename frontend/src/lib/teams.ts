// Team logo mapping for WPL teams
export const TEAM_LOGOS: Record<string, string> = {
    'MI': '/teams/mi.svg',
    'RCB': '/teams/rcb.svg',
    'UPW': '/teams/upw.png',
    'GG': '/teams/gg.svg',
    'DC': '/teams/dc.svg',
    // Add more teams as needed
    'IND': '/teams/ind.png',
    'AUS': '/teams/aus.png',
};

export function getTeamLogo(shortName: string): string {
    return TEAM_LOGOS[shortName] || '';
}
