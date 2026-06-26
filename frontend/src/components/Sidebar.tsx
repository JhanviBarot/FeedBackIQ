import { Link, useLocation } from 'react-router-dom';
import { X, LayoutDashboard, PlusCircle, History, Settings, HelpCircle } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/analyse/profile', label: 'New Analysis', icon: PlusCircle },
    { path: '/history', label: 'History', icon: History },
    { path: '/account', label: 'Account', icon: Settings },
  ];

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-black/30 z-40 lg:hidden" onClick={onClose} />
      )}

      <aside
        className={`fixed top-16 left-0 bottom-0 w-64 bg-white border-r border-gray-100 z-50 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-4 h-full flex flex-col">
          <div className="flex justify-end lg:hidden mb-4">
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="space-y-2 flex-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                location.pathname === item.path ||
                (item.path === '/analyse/profile' && location.pathname.startsWith('/analyse'));

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => onClose()}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                    isActive
                      ? 'gradient-bg text-white shadow-lg'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-muted'}`} />
                  <span className="font-medium">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto pt-4 border-t border-gray-100">
            <div className="gradient-bg-light rounded-xl p-4 border border-primary/10">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center">
                  <HelpCircle className="w-4 h-4 text-white" />
                </div>
                <p className="font-semibold text-gray-800 text-sm">Need help?</p>
              </div>
              <p className="text-xs text-muted mb-3">
                Check our documentation or contact support.
              </p>
              <button className="w-full text-sm text-primary font-medium hover:underline">
                View Docs
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
