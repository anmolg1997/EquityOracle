import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';

const navItems = [
  { to: '/', label: 'Command Center', icon: '◈' },
  { to: '/scanner', label: 'Scanner', icon: '⊞' },
  { to: '/recommendations', label: 'Recommendations', icon: '◉' },
  { to: '/portfolio', label: 'Portfolio', icon: '▦' },
  { to: '/performance', label: 'Performance', icon: '◫' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
];

export function Sidebar() {
  return (
    <nav className="w-56 bg-gray-900/80 border-r border-gray-800 flex flex-col py-4 shrink-0 h-full overflow-hidden">
      <div className="px-4 mb-6">
        <h1 className="text-lg font-bold text-brand-400 tracking-tight">EquityOracle</h1>
        <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-0.5">Command Center</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-2">
        <div className="flex flex-col gap-0.5 pb-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600/20 text-brand-300'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
                )
              }
            >
              <span className="text-base w-5 text-center">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </div>
      </div>

      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-[10px] text-gray-600">v0.1.0 · India</p>
      </div>
    </nav>
  );
}
