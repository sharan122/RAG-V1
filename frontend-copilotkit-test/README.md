# 🚀 RAG System - CopilotKit Frontend

A modern, AI-powered frontend for your RAG (Retrieval-Augmented Generation) system, built with React, TypeScript, Tailwind CSS, and CopilotKit.

## ✨ Features

- **🤖 AI Chat Interface** - Ask questions about your API documentation
- **📚 Document Management** - Upload and manage documentation files
- **🔗 Smart cURL Generator** - Generate perfect cURL commands for any endpoint
- **🎨 Modern UI** - Beautiful, responsive design with Tailwind CSS
- **📱 Mobile Friendly** - Responsive design that works on all devices
- **⚡ Real-time AI** - Instant responses powered by CopilotKit

## 🛠️ Tech Stack

- **Frontend**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **AI Integration**: CopilotKit
- **Build Tool**: Vite
- **Icons**: Lucide React
- **HTTP Client**: Axios

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Your RAG backend running on `http://localhost:8000`

### Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend-sample
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Navigate to `http://localhost:3000`

## 🔧 Configuration

### Backend API

The frontend is configured to proxy API requests to your backend at `http://localhost:8000`. You can modify this in `vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000', // Change this to your backend URL
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

### Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_COPILOTKIT_API_KEY=your_api_key_here
```

## 📱 Usage

### 1. AI Chat Tab
- Ask questions about your API documentation
- Get instant AI-powered responses
- Perfect for understanding API endpoints and usage

### 2. Documentation Tab
- View system status and document count
- Upload new documentation files
- Monitor RAG system health

### 3. cURL Generator Tab
- Generate perfect cURL commands for any endpoint
- Examples:
  - `"create curl for all POST endpoints in the doc"`
  - `"generate curl for /file-upload endpoint"`
  - `"create curl commands for file operations"`

## 🎨 Customization

### Colors and Theme

Modify `tailwind.config.js` to customize colors:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        500: '#your-brand-color',
        // ... other shades
      }
    }
  }
}
```

### Components

All components are located in `src/components/` and can be easily customized:

- `Header.tsx` - Navigation header
- `Sidebar.tsx` - Document management sidebar
- `MainContent.tsx` - Main content with tabs

### Styling

Custom CSS classes are defined in `src/index.css`:

```css
@layer components {
  .btn-primary {
    @apply bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-lg;
  }
  
  .card {
    @apply bg-white rounded-xl shadow-sm border border-gray-200 p-6;
  }
}
```

## 🔌 API Integration

### Backend Endpoints

The frontend expects these backend endpoints:

- `POST /docs/process` - Upload documentation
- `POST /docs/clear` - Clear all documents
- `GET /docs/status` - Get system status
- `POST /questions/ask` - Ask questions (AI chat)

### CopilotKit Integration

CopilotKit is configured to work with your existing backend:

```typescript
<CopilotChat
  apiEndpoint="/api/questions/ask"
  apiHeaders={{
    'Content-Type': 'application/json',
  }}
  apiBody={{
    session_id: 'default',
  }}
/>
```

## 📦 Build and Deploy

### Production Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

### Deploy

The `dist/` folder contains your production build that can be deployed to any static hosting service:

- Vercel
- Netlify
- AWS S3
- GitHub Pages

## 🐛 Troubleshooting

### Common Issues

1. **Backend Connection Error**
   - Ensure your backend is running on `http://localhost:8000`
   - Check the proxy configuration in `vite.config.ts`

2. **CopilotKit Not Working**
   - Verify your API endpoints are accessible
   - Check browser console for errors
   - Ensure proper CORS configuration on backend

3. **Styling Issues**
   - Clear browser cache
   - Restart the development server
   - Check Tailwind CSS compilation

### Debug Mode

Enable debug logging by adding to your browser console:

```javascript
localStorage.setItem('copilotkit-debug', 'true')
```

## 🔄 Updates and Maintenance

### Keeping Dependencies Updated

```bash
npm update
npm audit fix
```

### Adding New Features

1. Create new components in `src/components/`
2. Add new tabs in `MainContent.tsx`
3. Update the RAG context if needed
4. Test thoroughly before deployment

## 📚 Additional Resources

- [CopilotKit Documentation](https://docs.copilotkit.ai/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---

**Happy coding! 🚀✨**
