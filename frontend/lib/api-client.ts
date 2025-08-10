// API client with ngrok support
export const apiClient = {
  async get(path: string) {
    const response = await fetch(path, {
      headers: {
        'Accept': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`API call failed: ${response.status}`);
    }
    
    return response.json();
  }
};