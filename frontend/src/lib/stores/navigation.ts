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
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setCurrentPage: (page) => set({ currentPage: page }),
}));
