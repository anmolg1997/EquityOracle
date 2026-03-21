import axios from 'axios';

export const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

export const fetcher = async <T>(url: string): Promise<T> => {
  const { data } = await api.get<T>(url);
  return data;
};
