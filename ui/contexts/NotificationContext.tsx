"use client";

import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { useAuth } from './AuthContext';

interface Notification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: Date;
  read: boolean;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
}

type NotificationAction =
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'MARK_READ'; payload: { id: string } }
  | { type: 'MARK_ALL_READ' }
  | { type: 'SET_NOTIFICATIONS'; payload: Notification[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

const initialState: NotificationState = {
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null
};

function notificationReducer(state: NotificationState, action: NotificationAction): NotificationState {
  switch (action.type) {
    case 'ADD_NOTIFICATION':
      return {
        ...state,
        notifications: [action.payload, ...state.notifications],
        unreadCount: state.unreadCount + 1
      };
    case 'MARK_READ':
      return {
        ...state,
        notifications: state.notifications.map(n => 
          n.id === action.payload.id ? { ...n, read: true } : n
        ),
        unreadCount: state.unreadCount - 1 < 0 ? 0 : state.unreadCount - 1
      };
    case 'MARK_ALL_READ':
      return {
        ...state,
        notifications: state.notifications.map(n => ({ ...n, read: true })),
        unreadCount: 0
      };
    case 'SET_NOTIFICATIONS':
      return {
        ...state,
        notifications: action.payload,
        unreadCount: action.payload.filter(n => !n.read).length
      };
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload
      };
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload
      };
    default:
      return state;
  }
}

const NotificationContext = createContext<{
  state: NotificationState;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
} | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(notificationReducer, initialState);
  const { user } = useAuth();

  // Function to add a notification
  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    dispatch({
      type: 'ADD_NOTIFICATION',
      payload: {
        ...notification,
        id: crypto.randomUUID(),
        timestamp: new Date(),
        read: false
      }
    });
  };

  // Function to mark a notification as read
  const markAsRead = (id: string) => {
    dispatch({
      type: 'MARK_READ',
      payload: { id }
    });
  };

  // Function to mark all notifications as read
  const markAllAsRead = () => {
    dispatch({ type: 'MARK_ALL_READ' });
  };

  // Load notifications when user changes
  useEffect(() => {
    const fetchNotifications = async () => {
      if (!user) return;
      
      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        // Here you would call your API to get notifications
        // const response = await fetch('/api/v1/notifications');
        // const data = await response.json();
        // dispatch({ type: 'SET_NOTIFICATIONS', payload: data.notifications });
        
        // For now, just clear notifications when user changes
        dispatch({ type: 'SET_NOTIFICATIONS', payload: [] });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: 'Failed to load notifications' });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    fetchNotifications();
  }, [user]);

  return (
    <NotificationContext.Provider value={{ state, addNotification, markAsRead, markAllAsRead }}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};
