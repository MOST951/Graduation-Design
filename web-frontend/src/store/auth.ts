import { defineStore } from 'pinia';

interface User {
  id: number;
  username: string;
  name: string;
  email: string;
  role: string;
  avatar: string;
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null') as User | null,
  }),
  actions: {
    setToken(token: string) {
      this.token = token;
      localStorage.setItem('token', token);
    },
    setUser(user: User) {
      this.user = user;
      localStorage.setItem('user', JSON.stringify(user));
    },
    logout() {
      this.token = '';
      this.user = null;
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    },
    // 模拟登录（后端未启动时使用）
    mockLogin(username: string, password: string): boolean {
      const mockUsers: Record<string, { password: string; user: User }> = {
        admin: {
          password: 'admin123',
          user: { id: 1, username: 'admin', name: '系统管理员', email: 'admin@example.com', role: 'admin', avatar: '' },
        },
        user01: {
          password: 'user123',
          user: { id: 2, username: 'user01', name: '普通用户', email: 'user01@example.com', role: 'user', avatar: '' },
        },
      };
      const entry = mockUsers[username];
      if (entry && entry.password === password) {
        this.setToken('mock-token-' + Date.now());
        this.setUser(entry.user);
        return true;
      }
      return false;
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.token,
    currentUser: (state) => state.user,
    isAdmin: (state) => state.user?.role === 'admin',
  },
});
