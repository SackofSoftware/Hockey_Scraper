import React, { useState } from 'react';

// ============================================================================
// YOUTH HOCKEY DASHBOARD - Interactive Prototype
// ============================================================================
// API Base: http://localhost:8000/api/v1
// Season IDs: 10776 (Bay State Hockey League), 10477 (Eastern Hockey Federation)
// ============================================================================

// Logo mapping - maps team names to logo files in /logos/ directory
const LOGO_MAP = {
  'WHK': 'WHK.svg',
  'WHK Hawks': 'WHK.svg',
  'Hingham': 'hingham.svg',
  'Hanover': 'hanover.svg',
  'Marshfield': 'marshfield.svg',
  'Scituate': 'scituate.svg',
  'Norwell': 'norwell.svg',
  'Duxbury': 'duxbury.svg',
  'Plymouth': 'plymouth.svg',
  'Braintree': 'braintree.svg',
  'Weymouth': 'weymouth.svg',
  'Milton': 'milton.svg',
  'Pembroke': 'pembroke.svg',
  'Rockland': 'rockland.svg',
  'Silver Lake': 'silverlake.svg',
  'Cohasset Hull': 'cohasset_hull.svg',
  'Canton': 'canton.svg',
  'Bay State Breakers': 'bay_state_breakers.svg',
  'South Shore Eagles': 'south_shore_eagles.svg',
  'South Shore Seahawks': 'south_shore_seahawks.svg',
  'Beantown Bullies': 'beantown_bullies.svg',
  'Cape Cod Gulls': 'cape_cod_gulls.svg',
  'Cape Cod Waves': 'capecodwaves.svg',
  'Tri County': 'tricounty.svg',
  'Barnstable': 'barnstable.svg',
  'Sandwich': 'sandwich.svg',
  'Bourne': 'bourne.svg',
  'North Shore Shamrocks': 'Northshoreshamrocks.svg',
  'Northstars': 'Northstars.svg',
  'Minuteman': 'Minuteman.svg',
  'Abington': 'Abington_youht_hockey.svg',
  'KP Walpole': 'kp_walpole.svg',
  'Walpole': 'walpole.svg',
  'SC Panthers': 'sc_panthers.svg',
  'Spartans': 'Spartans.svg',
  'Vikings': 'vikings.svg',
  'Noreasters': 'noreasters.svg',
};

// Sample data structure matching API responses
const MOCK_DATA = {
  season: {
    season_id: "10776",
    title: "Bay State Hockey League 2024-25",
    sport: "hockey",
    association: "USAH - Massachusetts District",
    divisions_count: 8,
    teams_count: 64,
    games_count: 320
  },
  divisions: [
    { division_id: 101, division_name: "U10C South", teams_count: 8, games_count: 40 },
    { division_id: 102, division_name: "U10B South", teams_count: 8, games_count: 40 },
    { division_id: 103, division_name: "U12C South", teams_count: 8, games_count: 40 },
    { division_id: 104, division_name: "U12B South", teams_count: 8, games_count: 40 },
    { division_id: 105, division_name: "U14B South", teams_count: 8, games_count: 40 },
    { division_id: 106, division_name: "U14C South", teams_count: 8, games_count: 40 },
  ],
  standings: {
    101: [
      { rank: 1, team_id: 1001, team_name: "WHK Hawks", division: "U10C South", gp: 12, w: 10, l: 1, t: 1, gf: 48, ga: 18, pts: 21 },
      { rank: 2, team_id: 1002, team_name: "Hingham", division: "U10C South", gp: 12, w: 9, l: 2, t: 1, gf: 42, ga: 22, pts: 19 },
      { rank: 3, team_id: 1003, team_name: "Marshfield", division: "U10C South", gp: 12, w: 8, l: 3, t: 1, gf: 38, ga: 24, pts: 17 },
      { rank: 4, team_id: 1004, team_name: "Hanover", division: "U10C South", gp: 12, w: 7, l: 4, t: 1, gf: 35, ga: 28, pts: 15 },
      { rank: 5, team_id: 1005, team_name: "Scituate", division: "U10C South", gp: 12, w: 6, l: 5, t: 1, gf: 32, ga: 30, pts: 13 },
      { rank: 6, team_id: 1006, team_name: "Norwell", division: "U10C South", gp: 12, w: 4, l: 6, t: 2, gf: 28, ga: 35, pts: 10 },
      { rank: 7, team_id: 1007, team_name: "Duxbury", division: "U10C South", gp: 12, w: 2, l: 8, t: 2, gf: 20, ga: 42, pts: 6 },
      { rank: 8, team_id: 1008, team_name: "Plymouth", division: "U10C South", gp: 12, w: 1, l: 10, t: 1, gf: 15, ga: 52, pts: 3 },
    ],
    102: [
      { rank: 1, team_id: 2001, team_name: "South Shore Eagles", division: "U10B South", gp: 12, w: 11, l: 1, t: 0, gf: 55, ga: 15, pts: 22 },
      { rank: 2, team_id: 2002, team_name: "Braintree", division: "U10B South", gp: 12, w: 9, l: 2, t: 1, gf: 45, ga: 20, pts: 19 },
      { rank: 3, team_id: 2003, team_name: "Canton", division: "U10B South", gp: 12, w: 8, l: 3, t: 1, gf: 40, ga: 25, pts: 17 },
      { rank: 4, team_id: 2004, team_name: "Weymouth", division: "U10B South", gp: 12, w: 6, l: 5, t: 1, gf: 35, ga: 30, pts: 13 },
      { rank: 5, team_id: 2005, team_name: "Milton", division: "U10B South", gp: 12, w: 5, l: 6, t: 1, gf: 30, ga: 32, pts: 11 },
      { rank: 6, team_id: 2006, team_name: "Rockland", division: "U10B South", gp: 12, w: 4, l: 7, t: 1, gf: 28, ga: 38, pts: 9 },
      { rank: 7, team_id: 2007, team_name: "Cohasset Hull", division: "U10B South", gp: 12, w: 2, l: 9, t: 1, gf: 18, ga: 45, pts: 5 },
      { rank: 8, team_id: 2008, team_name: "Pembroke", division: "U10B South", gp: 12, w: 1, l: 10, t: 1, gf: 12, ga: 55, pts: 3 },
    ],
    103: [
      { rank: 1, team_id: 3001, team_name: "Bay State Breakers", division: "U12C South", gp: 14, w: 12, l: 1, t: 1, gf: 62, ga: 18, pts: 25 },
      { rank: 2, team_id: 3002, team_name: "Tri County", division: "U12C South", gp: 14, w: 10, l: 3, t: 1, gf: 52, ga: 25, pts: 21 },
      { rank: 3, team_id: 3003, team_name: "Cape Cod Waves", division: "U12C South", gp: 14, w: 9, l: 4, t: 1, gf: 48, ga: 28, pts: 19 },
      { rank: 4, team_id: 3004, team_name: "Barnstable", division: "U12C South", gp: 14, w: 7, l: 5, t: 2, gf: 40, ga: 32, pts: 16 },
      { rank: 5, team_id: 3005, team_name: "Sandwich", division: "U12C South", gp: 14, w: 6, l: 6, t: 2, gf: 35, ga: 38, pts: 14 },
      { rank: 6, team_id: 3006, team_name: "Bourne", division: "U12C South", gp: 14, w: 4, l: 8, t: 2, gf: 28, ga: 45, pts: 10 },
      { rank: 7, team_id: 3007, team_name: "Silver Lake", division: "U12C South", gp: 14, w: 2, l: 10, t: 2, gf: 20, ga: 52, pts: 6 },
      { rank: 8, team_id: 3008, team_name: "Abington", division: "U12C South", gp: 14, w: 1, l: 12, t: 1, gf: 15, ga: 60, pts: 3 },
    ],
  },
  teams: {
    1001: {
      team_id: 1001,
      team_name: "WHK Hawks",
      division_id: 101,
      division_name: "U10C South",
      record: { gp: 12, w: 10, l: 1, t: 1, pts: 21, pts_pct: 0.875 },
      scoring: { gf: 48, ga: 18, diff: 30, gpg: 4.0, gapg: 1.5 },
      recent_form: { last_5: "W-W-W-L-W", streak: "W2" },
      roster: [
        { id: "p1", number: 9, name: "Brady Smith", position: "C", gp: 12, g: 15, a: 12, pts: 27, pim: 4 },
        { id: "p2", number: 11, name: "Tyler Johnson", position: "LW", gp: 12, g: 10, a: 8, pts: 18, pim: 6 },
        { id: "p3", number: 7, name: "Jake Wilson", position: "RW", gp: 12, g: 8, a: 10, pts: 18, pim: 2 },
        { id: "p4", number: 4, name: "Ryan Murphy", position: "D", gp: 12, g: 3, a: 12, pts: 15, pim: 8 },
        { id: "p5", number: 21, name: "Connor Brown", position: "D", gp: 12, g: 2, a: 10, pts: 12, pim: 4 },
        { id: "p6", number: 14, name: "Matt Davis", position: "C", gp: 12, g: 5, a: 6, pts: 11, pim: 2 },
        { id: "p7", number: 17, name: "Luke Anderson", position: "LW", gp: 10, g: 3, a: 5, pts: 8, pim: 0 },
        { id: "p8", number: 22, name: "Sam Taylor", position: "RW", gp: 11, g: 2, a: 4, pts: 6, pim: 2 },
        { id: "p9", number: 30, name: "Alex Garcia", position: "G", gp: 10, g: 0, a: 0, pts: 0, pim: 0, gaa: 1.5, sv: 0.925 },
      ],
      schedule: [
        { id: "g1", date: "2025-01-18", time: "7:00 PM", opponent: "Hingham", home: true, score: "4-2", result: "W" },
        { id: "g2", date: "2025-01-25", time: "8:00 PM", opponent: "Marshfield", home: false, score: "5-1", result: "W" },
        { id: "g3", date: "2025-02-01", time: "6:00 PM", opponent: "Hanover", home: true, score: null, result: null },
        { id: "g4", date: "2025-02-08", time: "7:30 PM", opponent: "Scituate", home: false, score: null, result: null },
      ]
    },
    1002: {
      team_id: 1002,
      team_name: "Hingham",
      division_id: 101,
      division_name: "U10C South",
      record: { gp: 12, w: 9, l: 2, t: 1, pts: 19, pts_pct: 0.792 },
      scoring: { gf: 42, ga: 22, diff: 20, gpg: 3.5, gapg: 1.83 },
      recent_form: { last_5: "W-L-W-W-W", streak: "W3" },
      roster: [
        { id: "p10", number: 19, name: "Jack Miller", position: "C", gp: 12, g: 12, a: 10, pts: 22, pim: 2 },
        { id: "p11", number: 8, name: "Ben Thompson", position: "LW", gp: 12, g: 9, a: 7, pts: 16, pim: 4 },
        { id: "p12", number: 15, name: "Dylan White", position: "RW", gp: 12, g: 7, a: 8, pts: 15, pim: 2 },
      ],
      schedule: []
    },
  }
};

// Team Logo Component
const TeamLogo = ({ teamName, size = 48, className = "" }) => {
  const logoFile = LOGO_MAP[teamName] || LOGO_MAP[teamName.split(' ')[0]];
  const fallbackInitials = teamName.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  if (logoFile) {
    return (
      <div
        className={`rounded-full bg-gray-100 flex items-center justify-center overflow-hidden ${className}`}
        style={{ width: size, height: size }}
      >
        <img
          src={`logos/${logoFile}`}
          alt={teamName}
          className="w-full h-full object-contain p-1"
          onError={(e) => {
            e.target.style.display = 'none';
            e.target.nextSibling.style.display = 'flex';
          }}
        />
        <div
          className="w-full h-full items-center justify-center bg-gradient-to-br from-blue-600 to-blue-800 text-white font-bold"
          style={{ display: 'none', fontSize: size * 0.35 }}
        >
          {fallbackInitials}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-full bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center text-white font-bold ${className}`}
      style={{ width: size, height: size, fontSize: size * 0.35 }}
    >
      {fallbackInitials}
    </div>
  );
};

// API Endpoint Badge
const APIBadge = ({ endpoint, method = "GET" }) => (
  <div className="inline-flex items-center gap-1.5 bg-gray-900 text-gray-300 px-2 py-1 rounded text-xs font-mono">
    <span className={`font-semibold ${method === 'GET' ? 'text-green-400' : 'text-blue-400'}`}>{method}</span>
    <span className="text-gray-400">{endpoint}</span>
  </div>
);

// Stats Card Component
const StatCard = ({ label, value, subtext, trend }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
    <div className="text-sm text-gray-500 uppercase tracking-wide font-medium">{label}</div>
    <div className="text-3xl font-bold text-gray-900 mt-1">{value}</div>
    {subtext && <div className="text-sm text-gray-500 mt-1">{subtext}</div>}
    {trend && (
      <div className={`text-sm mt-1 ${trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500'}`}>
        {trend > 0 ? '↑' : trend < 0 ? '↓' : '–'} {Math.abs(trend)}
      </div>
    )}
  </div>
);

// Standings Table Row
const StandingsRow = ({ team, onTeamClick }) => (
  <tr
    className="hover:bg-blue-50 cursor-pointer transition-colors border-b border-gray-100"
    onClick={() => onTeamClick(team.team_id)}
  >
    <td className="py-3 px-4 text-center font-semibold text-gray-600">{team.rank}</td>
    <td className="py-3 px-4">
      <div className="flex items-center gap-3">
        <TeamLogo teamName={team.team_name} size={36} />
        <div>
          <div className="font-semibold text-gray-900">{team.team_name}</div>
          <div className="text-xs text-gray-500">{team.division}</div>
        </div>
      </div>
    </td>
    <td className="py-3 px-4 text-center font-medium">{team.gp}</td>
    <td className="py-3 px-4 text-center text-green-700 font-medium">{team.w}</td>
    <td className="py-3 px-4 text-center text-red-700 font-medium">{team.l}</td>
    <td className="py-3 px-4 text-center text-gray-600">{team.t}</td>
    <td className="py-3 px-4 text-center">{team.gf}</td>
    <td className="py-3 px-4 text-center">{team.ga}</td>
    <td className="py-3 px-4 text-center font-medium" style={{ color: team.gf - team.ga > 0 ? '#059669' : team.gf - team.ga < 0 ? '#dc2626' : '#6b7280' }}>
      {team.gf - team.ga > 0 ? '+' : ''}{team.gf - team.ga}
    </td>
    <td className="py-3 px-4 text-center font-bold text-blue-700">{team.pts}</td>
  </tr>
);

// Division Card for Overview
const DivisionCard = ({ division, standings, onDivisionClick, onTeamClick }) => {
  const topTeams = standings?.slice(0, 3) || [];

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => onDivisionClick(division.division_id)}
    >
      <div className="bg-gradient-to-r from-blue-900 to-blue-700 px-4 py-3">
        <h3 className="text-white font-bold text-lg">{division.division_name}</h3>
        <div className="text-blue-200 text-sm">{division.teams_count} Teams • {division.games_count} Games</div>
      </div>

      <div className="p-4">
        <div className="flex items-center gap-3 mb-3">
          {topTeams.map((team, idx) => (
            <div key={team.team_id} className="flex items-center gap-2" onClick={(e) => { e.stopPropagation(); onTeamClick(team.team_id); }}>
              <div className="relative">
                <TeamLogo teamName={team.team_name} size={idx === 0 ? 48 : 40} />
                <div className={`absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold
                  ${idx === 0 ? 'bg-yellow-400 text-yellow-900' : idx === 1 ? 'bg-gray-300 text-gray-700' : 'bg-amber-600 text-amber-100'}`}>
                  {idx + 1}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          {topTeams.map((team, idx) => (
            <div
              key={team.team_id}
              className="flex items-center justify-between text-sm hover:bg-gray-50 rounded px-2 py-1"
              onClick={(e) => { e.stopPropagation(); onTeamClick(team.team_id); }}
            >
              <span className="font-medium">{idx + 1}. {team.team_name}</span>
              <span className="text-gray-600">{team.w}-{team.l}-{team.t} • <span className="font-semibold text-blue-700">{team.pts} pts</span></span>
            </div>
          ))}
        </div>

        <div className="mt-3 text-center">
          <span className="text-blue-600 text-sm font-medium hover:underline">View Full Standings →</span>
        </div>
      </div>
    </div>
  );
};

// Team Detail View
const TeamDetailView = ({ teamId, onBack }) => {
  const team = MOCK_DATA.teams[teamId];

  if (!team) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-500">Team not found</p>
        <button onClick={onBack} className="mt-4 text-blue-600 hover:underline">← Back</button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Team Header */}
      <div className="bg-gradient-to-r from-blue-900 via-blue-800 to-blue-700 rounded-xl p-6 mb-6">
        <button onClick={onBack} className="text-blue-200 hover:text-white mb-4 flex items-center gap-1">
          ← Back to Standings
        </button>

        <div className="flex items-center gap-6">
          <TeamLogo teamName={team.team_name} size={96} className="border-4 border-white shadow-lg" />
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-white">{team.team_name}</h1>
            <p className="text-blue-200 text-lg">{team.division_name}</p>
            <div className="flex gap-4 mt-2">
              <span className="bg-blue-700/50 px-3 py-1 rounded text-white text-sm">
                Record: <strong>{team.record.w}-{team.record.l}-{team.record.t}</strong>
              </span>
              <span className="bg-blue-700/50 px-3 py-1 rounded text-white text-sm">
                Points: <strong>{team.record.pts}</strong>
              </span>
              <span className="bg-blue-700/50 px-3 py-1 rounded text-white text-sm">
                Streak: <strong>{team.recent_form.streak}</strong>
              </span>
            </div>
          </div>
        </div>

        <div className="mt-4 flex gap-2 flex-wrap">
          <APIBadge endpoint={`/api/v1/teams/${teamId}`} />
          <APIBadge endpoint={`/api/v1/teams/${teamId}/stats`} />
          <APIBadge endpoint={`/api/v1/teams/${teamId}/roster`} />
          <APIBadge endpoint={`/api/v1/teams/${teamId}/schedule`} />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Goals For" value={team.scoring.gf} subtext={`${team.scoring.gpg} per game`} />
        <StatCard label="Goals Against" value={team.scoring.ga} subtext={`${team.scoring.gapg} per game`} />
        <StatCard label="Goal Diff" value={team.scoring.diff > 0 ? `+${team.scoring.diff}` : team.scoring.diff} trend={team.scoring.diff} />
        <StatCard label="Points %" value={`${(team.record.pts_pct * 100).toFixed(1)}%`} />
      </div>

      {/* Roster Section */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
        <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Roster & Stats</h2>
          <APIBadge endpoint={`/api/v1/teams/${teamId}/roster`} />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">#</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Player</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">Pos</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">GP</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">G</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">A</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">PTS</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">PIM</th>
              </tr>
            </thead>
            <tbody>
              {team.roster.map((player, idx) => (
                <tr key={player.id} className={`border-b border-gray-100 ${idx % 2 === 1 ? 'bg-gray-50' : ''}`}>
                  <td className="py-3 px-4 font-semibold text-gray-600">{player.number}</td>
                  <td className="py-3 px-4 font-medium text-gray-900">{player.name}</td>
                  <td className="py-3 px-4 text-center text-gray-600">{player.position}</td>
                  <td className="py-3 px-4 text-center">{player.gp}</td>
                  <td className="py-3 px-4 text-center text-green-700 font-medium">{player.g}</td>
                  <td className="py-3 px-4 text-center text-blue-700 font-medium">{player.a}</td>
                  <td className="py-3 px-4 text-center font-bold">{player.pts}</td>
                  <td className="py-3 px-4 text-center text-gray-600">{player.pim}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Schedule Section */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Schedule</h2>
          <APIBadge endpoint={`/api/v1/teams/${teamId}/schedule`} />
        </div>

        <div className="divide-y divide-gray-100">
          {team.schedule.map((game) => (
            <div key={game.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50">
              <div className="flex items-center gap-4">
                <div className="text-center" style={{ minWidth: 80 }}>
                  <div className="text-sm font-medium text-gray-900">{game.date}</div>
                  <div className="text-xs text-gray-500">{game.time}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-medium px-2 py-1 rounded ${game.home ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                    {game.home ? 'HOME' : 'AWAY'}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">vs</span>
                    <TeamLogo teamName={game.opponent} size={32} />
                    <span className="font-medium text-gray-900">{game.opponent}</span>
                  </div>
                </div>
              </div>

              {game.result ? (
                <div className={`text-lg font-bold ${game.result === 'W' ? 'text-green-600' : game.result === 'L' ? 'text-red-600' : 'text-gray-600'}`}>
                  {game.result} {game.score}
                </div>
              ) : (
                <div className="text-gray-400 text-sm">Upcoming</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Division Standings View
const DivisionStandingsView = ({ divisionId, onBack, onTeamClick }) => {
  const division = MOCK_DATA.divisions.find(d => d.division_id === divisionId);
  const standings = MOCK_DATA.standings[divisionId] || [];

  return (
    <div className="max-w-5xl mx-auto">
      <button onClick={onBack} className="text-blue-600 hover:underline mb-4 flex items-center gap-1">
        ← Back to All Divisions
      </button>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-blue-900 to-blue-700 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">{division?.division_name} Standings</h2>
            <p className="text-blue-200">{standings.length} Teams</p>
          </div>
          <APIBadge endpoint={`/api/v1/divisions/${divisionId}/standings`} />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase w-12">RK</th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Team</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">GP</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">W</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">L</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">T</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">GF</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">GA</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">DIFF</th>
                <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase">PTS</th>
              </tr>
            </thead>
            <tbody>
              {standings.map((team) => (
                <StandingsRow key={team.team_id} team={team} onTeamClick={onTeamClick} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Main Dashboard
const HockeyDashboard = () => {
  const [view, setView] = useState('overview'); // 'overview', 'division', 'team'
  const [selectedDivision, setSelectedDivision] = useState(null);
  const [selectedTeam, setSelectedTeam] = useState(null);

  const handleDivisionClick = (divisionId) => {
    setSelectedDivision(divisionId);
    setView('division');
  };

  const handleTeamClick = (teamId) => {
    setSelectedTeam(teamId);
    setView('team');
  };

  const handleBack = () => {
    if (view === 'team') {
      setView(selectedDivision ? 'division' : 'overview');
      setSelectedTeam(null);
    } else if (view === 'division') {
      setView('overview');
      setSelectedDivision(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-gray-900 via-blue-900 to-gray-900 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-8 h-8 text-blue-900" fill="currentColor">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"/>
                  <circle cx="12" cy="12" r="2" fill="currentColor"/>
                  <line x1="12" y1="2" x2="12" y2="6" stroke="currentColor" strokeWidth="2"/>
                  <line x1="12" y1="18" x2="12" y2="22" stroke="currentColor" strokeWidth="2"/>
                  <line x1="2" y1="12" x2="6" y2="12" stroke="currentColor" strokeWidth="2"/>
                  <line x1="18" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="2"/>
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">{MOCK_DATA.season.title}</h1>
                <p className="text-blue-300 text-sm">{MOCK_DATA.season.association}</p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-white">
              <div className="text-center px-4 border-r border-blue-700">
                <div className="text-2xl font-bold">{MOCK_DATA.season.divisions_count}</div>
                <div className="text-xs text-blue-300 uppercase">Divisions</div>
              </div>
              <div className="text-center px-4 border-r border-blue-700">
                <div className="text-2xl font-bold">{MOCK_DATA.season.teams_count}</div>
                <div className="text-xs text-blue-300 uppercase">Teams</div>
              </div>
              <div className="text-center px-4">
                <div className="text-2xl font-bold">{MOCK_DATA.season.games_count}</div>
                <div className="text-xs text-blue-300 uppercase">Games</div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* API Info Bar */}
      <div className="bg-gray-800 py-2 px-6">
        <div className="max-w-7xl mx-auto flex items-center gap-4 text-sm">
          <span className="text-gray-400">API Endpoints:</span>
          <APIBadge endpoint="/api/v1/seasons/10776" />
          <APIBadge endpoint="/api/v1/seasons/10776/divisions" />
          <span className="text-gray-500 ml-auto">Base: http://localhost:8000</span>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {view === 'overview' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Divisions</h2>
              <APIBadge endpoint="/api/v1/seasons/10776/divisions" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {MOCK_DATA.divisions.map((division) => (
                <DivisionCard
                  key={division.division_id}
                  division={division}
                  standings={MOCK_DATA.standings[division.division_id]}
                  onDivisionClick={handleDivisionClick}
                  onTeamClick={handleTeamClick}
                />
              ))}
            </div>

            {/* Quick Stats Section */}
            <div className="mt-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">League Leaders</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Top Teams */}
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <div className="bg-gradient-to-r from-yellow-500 to-yellow-600 px-4 py-3">
                    <h3 className="text-white font-bold">Top Teams by Points</h3>
                  </div>
                  <div className="p-4 space-y-3">
                    {[
                      { name: "South Shore Eagles", pts: 22, division: "U10B" },
                      { name: "Bay State Breakers", pts: 25, division: "U12C" },
                      { name: "WHK Hawks", pts: 21, division: "U10C" },
                    ].map((team, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-bold text-gray-600">
                          {idx + 1}
                        </div>
                        <TeamLogo teamName={team.name} size={36} />
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{team.name}</div>
                          <div className="text-xs text-gray-500">{team.division}</div>
                        </div>
                        <div className="font-bold text-blue-700">{team.pts} pts</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Best Offense */}
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <div className="bg-gradient-to-r from-green-500 to-green-600 px-4 py-3">
                    <h3 className="text-white font-bold">Best Offense (Goals/Game)</h3>
                  </div>
                  <div className="p-4 space-y-3">
                    {[
                      { name: "South Shore Eagles", gpg: 4.58, division: "U10B" },
                      { name: "Bay State Breakers", gpg: 4.43, division: "U12C" },
                      { name: "WHK Hawks", gpg: 4.0, division: "U10C" },
                    ].map((team, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-bold text-gray-600">
                          {idx + 1}
                        </div>
                        <TeamLogo teamName={team.name} size={36} />
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{team.name}</div>
                          <div className="text-xs text-gray-500">{team.division}</div>
                        </div>
                        <div className="font-bold text-green-700">{team.gpg} G/G</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Best Defense */}
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <div className="bg-gradient-to-r from-red-500 to-red-600 px-4 py-3">
                    <h3 className="text-white font-bold">Best Defense (GA/Game)</h3>
                  </div>
                  <div className="p-4 space-y-3">
                    {[
                      { name: "South Shore Eagles", gapg: 1.25, division: "U10B" },
                      { name: "Bay State Breakers", gapg: 1.29, division: "U12C" },
                      { name: "WHK Hawks", gapg: 1.5, division: "U10C" },
                    ].map((team, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-bold text-gray-600">
                          {idx + 1}
                        </div>
                        <TeamLogo teamName={team.name} size={36} />
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{team.name}</div>
                          <div className="text-xs text-gray-500">{team.division}</div>
                        </div>
                        <div className="font-bold text-red-700">{team.gapg} GA/G</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {view === 'division' && selectedDivision && (
          <DivisionStandingsView
            divisionId={selectedDivision}
            onBack={handleBack}
            onTeamClick={handleTeamClick}
          />
        )}

        {view === 'team' && selectedTeam && (
          <TeamDetailView
            teamId={selectedTeam}
            onBack={handleBack}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-sm">
              Youth Hockey Stats Dashboard • Powered by GameSheet API
            </div>
            <div className="flex gap-4 text-sm">
              <span>Season: {MOCK_DATA.season.season_id}</span>
              <span>•</span>
              <span>42 Team Logos Loaded</span>
              <span>•</span>
              <span>FastAPI Backend</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HockeyDashboard;
