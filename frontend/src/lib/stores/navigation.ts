import { create } from 'zustand';

interface NavigationState {
  sidebarCollapsed: boolean;
  currentPage: string;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setCurrentPage: (page: string) => void;
}

export const useNavigationStore = create<NavigationState>((set) => ({
  sidebarCollapsed: false,
  currentPage: 'dashboard',
  setSidebarCollapsed: (collapsed: boolean) => set({ sidebarCollapsed: collapsed }),
  setCurrentPage: (page: string) => set({ currentPage: page }),
}));
