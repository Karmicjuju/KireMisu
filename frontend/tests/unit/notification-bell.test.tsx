/**
 * Unit Tests for NotificationBell Component
 * Following the testing strategy: Jest + React Testing Library
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { NotificationBell } from '@/components/notifications/notification-bell';
import { TEST_NOTIFICATIONS_DATA, TestDataManager } from '../fixtures/manga-test-data';

// Mock the hooks and components
jest.mock('@/hooks/use-notifications', () => ({
  useNotifications: jest.fn()
}));

jest.mock('@/components/notifications/notification-dropdown', () => ({
  NotificationDropdown: ({ isOpen, notifications, isLoading }) => {
    const React = require('react');
    return React.createElement('div', {
      'data-testid': 'notification-dropdown',
      style: { display: isOpen ? 'block' : 'none' }
    }, isLoading ? 'Loading...' : `${notifications.length} notifications`);
  }
}));

describe('NotificationBell Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render notification bell button', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: [],
        isLoading: false
      });

      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toBeInTheDocument();
      expect(bell).toHaveAttribute('aria-label', 'Notifications ');
    });

    it('should show unread count badge when there are unread notifications', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      const unreadNotifications = TestDataManager.getUnreadNotifications();
      
      useNotifications.mockReturnValue({
        data: TEST_NOTIFICATIONS_DATA,
        isLoading: false
      });

      render(<NotificationBell />);

      const badge = screen.getByTestId('notification-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(unreadNotifications.length.toString());
    });

    it('should not show badge when all notifications are read', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      const readNotifications = TEST_NOTIFICATIONS_DATA.map(n => ({ ...n, is_read: true }));
      
      useNotifications.mockReturnValue({
        data: readNotifications,
        isLoading: false
      });

      render(<NotificationBell />);

      const badge = screen.queryByTestId('notification-badge');
      expect(badge).not.toBeInTheDocument();
    });

    it('should show "99+" for large unread counts', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      const manyNotifications = Array.from({ length: 150 }, (_, i) => ({
        id: `notification-${i}`,
        type: 'new_chapter',
        title: `Notification ${i}`,
        message: 'Test message',
        is_read: false,
        created_at: new Date().toISOString(),
        link: null
      }));
      
      useNotifications.mockReturnValue({
        data: manyNotifications,
        isLoading: false
      });

      render(<NotificationBell />);

      const badge = screen.getByTestId('notification-badge');
      expect(badge).toHaveTextContent('99+');
    });
  });

  describe('User Interactions', () => {
    it('should open dropdown when clicked', async () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: TEST_NOTIFICATIONS_DATA,
        isLoading: false
      });

      const user = userEvent.setup();
      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      await user.click(bell);

      const dropdown = screen.getByTestId('notification-dropdown');
      expect(dropdown).toBeVisible();
    });

    it('should close dropdown when clicked again', async () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: TEST_NOTIFICATIONS_DATA,
        isLoading: false
      });

      const user = userEvent.setup();
      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      
      // Open dropdown
      await user.click(bell);
      let dropdown = screen.getByTestId('notification-dropdown');
      expect(dropdown).toBeVisible();

      // Close dropdown
      await user.click(bell);
      dropdown = screen.getByTestId('notification-dropdown');
      expect(dropdown).not.toBeVisible();
    });

    it('should be keyboard accessible', async () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: TEST_NOTIFICATIONS_DATA,
        isLoading: false
      });

      const user = userEvent.setup();
      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      bell.focus();
      expect(bell).toHaveFocus();

      await user.keyboard('{Enter}');
      const dropdown = screen.getByTestId('notification-dropdown');
      expect(dropdown).toBeVisible();
    });
  });

  describe('Loading States', () => {
    it('should handle loading state', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: undefined,
        isLoading: true
      });

      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toBeInTheDocument();
      
      // Should not show badge when loading
      const badge = screen.queryByTestId('notification-badge');
      expect(badge).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA label with unread count', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      const unreadCount = TestDataManager.getUnreadNotifications().length;
      
      useNotifications.mockReturnValue({
        data: TEST_NOTIFICATIONS_DATA,
        isLoading: false
      });

      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toHaveAttribute('aria-label', `Notifications (${unreadCount} unread)`);
    });

    it('should have proper ARIA label with no unread notifications', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      const readNotifications = TEST_NOTIFICATIONS_DATA.map(n => ({ ...n, is_read: true }));
      
      useNotifications.mockReturnValue({
        data: readNotifications,
        isLoading: false
      });

      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toHaveAttribute('aria-label', 'Notifications ');
    });

    it('should have correct button role and attributes', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: [],
        isLoading: false
      });

      render(<NotificationBell />);

      const bell = screen.getByRole('button');
      expect(bell).toHaveAttribute('data-testid', 'notification-bell');
    });
  });

  describe('Custom Styling', () => {
    it('should apply custom className', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: [],
        isLoading: false
      });

      render(<NotificationBell className="custom-class" />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toHaveClass('custom-class');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty notifications array', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: [],
        isLoading: false
      });

      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toBeInTheDocument();
      
      const badge = screen.queryByTestId('notification-badge');
      expect(badge).not.toBeInTheDocument();
    });

    it('should handle null notifications data', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: null,
        isLoading: false
      });

      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toBeInTheDocument();
      
      const badge = screen.queryByTestId('notification-badge');
      expect(badge).not.toBeInTheDocument();
    });

    it('should handle undefined notifications data', () => {
      const { useNotifications } = require('@/hooks/use-notifications');
      useNotifications.mockReturnValue({
        data: undefined,
        isLoading: false
      });

      render(<NotificationBell />);

      const bell = screen.getByTestId('notification-bell');
      expect(bell).toBeInTheDocument();
    });
  });
});