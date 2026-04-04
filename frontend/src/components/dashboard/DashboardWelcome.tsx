import React, { useState } from 'react';
import { Lightbulb, Layers, MessageSquare, Camera, Smile, Mic, Send } from 'lucide-react';
import logoTiktak from '../../assets/images/logoTiktak.png';

const DashboardWelcome = ({ onStartChat }) => {
    const [message, setMessage] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (message.trim() && onStartChat) {
            onStartChat(message);
            setMessage('');
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className="flex-1 flex flex-col items-center w-full h-full bg-[#fcfcfc] overflow-y-auto overflow-x-hidden">

            {/* Main Content Area */}
            <div className="flex-1 w-full max-w-4xl flex flex-col justify-center px-6 pt-4 pb-8 min-h-[500px]">

                {/* Hero Text */}
                <div className="text-center mb-10 mt-2">
                    <h1 className="text-[34px] md:text-[42px] font-extrabold text-[#2a303a] mb-3 tracking-tight drop-shadow-sm">AI &amp; Human Expertise</h1>
                    <p className="text-gray-500 text-[16px] md:text-lg tracking-wide font-medium">
                        Get instant answers with AI support and human expertise when needed.
                    </p>
                </div>

                {/* Feature Cards Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 md:gap-6 w-full mb-12 max-w-[850px] mx-auto">

                    <div className="bg-[#f0f3f9] p-7 rounded-3xl flex flex-col space-y-3 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg cursor-pointer group border border-transparent hover:border-gray-200">
                        <div className="flex items-center space-x-3.5 mb-1">
                            <div className="p-2.5 bg-white rounded-xl shadow-sm text-gray-700 group-hover:text-[#0f6885] group-hover:shadow transition-all group-hover:scale-110">
                                <Lightbulb className="w-5 h-5" />
                            </div>
                            <h3 className="text-[19px] font-extrabold text-[#2a303a]">Recommendations</h3>
                        </div>
                        <p className="text-[#3a414e] text-[16px] leading-relaxed font-semibold">
                            Get curated picks for a fresh and fashionable summer wardrobe.
                        </p>
                    </div>

                    <div className="bg-[#f0f3f9] p-7 rounded-3xl flex flex-col space-y-3 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg cursor-pointer group border border-transparent hover:border-gray-200">
                        <div className="flex items-center space-x-3.5 mb-1">
                            <div className="p-2.5 bg-white rounded-xl shadow-sm text-gray-700 group-hover:text-[#0f6885] group-hover:shadow transition-all group-hover:scale-110">
                                <Layers className="w-5 h-5" />
                            </div>
                            <h3 className="text-[19px] font-extrabold text-[#2a303a]">Comparison</h3>
                        </div>
                        <p className="text-[#3a414e] text-[16px] leading-relaxed font-semibold">
                            Compare features, pricing, and style at a glance.
                        </p>
                    </div>

                    <div className="bg-[#f0f3f9] p-7 rounded-3xl flex flex-col space-y-3 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg cursor-pointer group border border-transparent hover:border-gray-200">
                        <div className="flex items-center space-x-3.5 mb-1">
                            <div className="p-2.5 bg-white rounded-xl shadow-sm text-gray-700 group-hover:text-[#0f6885] group-hover:shadow transition-all group-hover:scale-110">
                                <MessageSquare className="w-5 h-5" />
                            </div>
                            <h3 className="text-[19px] font-extrabold text-[#2a303a]">Instant Chat</h3>
                        </div>
                        <p className="text-[#3a414e] text-[16px] leading-relaxed font-semibold">
                            Ask questions and receive real-time support.
                        </p>
                    </div>

                    <div className="bg-[#f0f3f9] p-7 rounded-3xl flex flex-col space-y-3 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg cursor-pointer group border border-transparent hover:border-gray-200">
                        <div className="flex items-center space-x-3.5 mb-1">
                            <div className="p-2.5 bg-white rounded-xl shadow-sm text-gray-700 group-hover:text-[#0f6885] group-hover:shadow transition-all group-hover:scale-110">
                                <Camera className="w-5 h-5" />
                            </div>
                            <h3 className="text-[19px] font-extrabold text-[#2a303a]">Image Search</h3>
                        </div>
                        <p className="text-[#3a414e] text-[16px] leading-relaxed font-semibold">
                            Upload a photo to find matching products.
                        </p>
                    </div>
                </div>

                {/* Input Area (Functional) */}
                <div className="w-full max-w-[850px] mx-auto mt-auto mb-2 relative shrink-0">
                    <form
                        onSubmit={handleSubmit}
                        className="relative flex items-center bg-white border border-gray-200 rounded-3xl p-3 shadow-[0_4px_25px_-8px_rgba(0,0,0,0.06)] transition-all hover:shadow-md hover:border-gray-300 group"
                    >
                        <button type="button" className="p-2.5 text-gray-400 hover:text-indigo-600 transition-colors hidden sm:block active:scale-95 ml-1">
                            <svg className="w-[22px] h-[22px] transform -rotate-45" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                            </svg>
                        </button>
                        <input
                            type="text"
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Message to Street Wear Agent..."
                            className="flex-1 bg-transparent border-none focus:outline-none focus:ring-0 text-gray-700 px-3 placeholder-gray-400 font-semibold text-[15.5px] cursor-text text-left"
                        />
                        <div className="flex items-center space-x-1 sm:space-x-2 mr-1">
                            <button type="button" className="p-2.5 text-gray-400 hover:text-gray-600 transition-colors active:scale-95"><Smile className="w-5 h-5" /></button>
                            <button type="button" className="p-2.5 text-gray-400 hover:text-gray-600 transition-colors active:scale-95"><Mic className="w-5 h-5" /></button>
                            <button
                                type="submit"
                                disabled={!message.trim()}
                                className={`text-white rounded-[22px] px-6 py-3 ml-2 flex items-center justify-center transition-all shadow-sm ${message.trim()
                                    ? 'bg-[#0f6885] hover:bg-[#0c5973] cursor-pointer hover:shadow-lg active:scale-95'
                                    : 'bg-[#a5c3cf] cursor-not-allowed'
                                    }`}
                            >
                                <span className="font-extrabold text-[15.5px] tracking-wide mr-2 hidden sm:block">Send</span>
                                <Send className="w-4 h-4 ml-0.5" />
                            </button>
                        </div>
                    </form>
                    <div className="flex justify-center mt-6 mb-2">
                        <span className="text-gray-400 text-[13.5px] font-semibold flex items-center tracking-wide">
                            Powered By <img src={logoTiktak} alt="Tiktak Logo" className="h-4 mx-1.5 drop-shadow-sm" /> <span className="text-gray-500 font-bold ml-1">Tiktak PRO</span>
                        </span>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default DashboardWelcome;
