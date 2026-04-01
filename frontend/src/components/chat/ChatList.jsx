import React, { useState } from 'react';
import { Search, MessageSquare } from 'lucide-react';

const ChatList = ({ chats, selectedChat, onSelectChat }) => {
    const [activeTab, setActiveTab] = useState('Recents');

    return (
        <div className="w-full max-w-[340px] bg-white border border-gray-100 shadow-sm rounded-2xl flex flex-col h-full flex-shrink-0 z-10 relative m-4 overflow-hidden">
            {/* Header */}
            <div className="p-6 pb-4 bg-white z-20">
                <div className="flex items-center justify-between mb-6 text-[#1c1d22]">
                    <h2 className="text-[26px] font-[800] tracking-tight text-[#1c1e21]">Chat List</h2>
                    <button className="w-10 h-10 rounded-xl border border-gray-200 flex items-center justify-center text-gray-500 hover:text-[#0f6885] hover:border-[#0f6885] hover:bg-indigo-50/50 transition-all active:scale-95 group">
                        <MessageSquare className="w-5 h-5 group-hover:scale-110 transition-transform" strokeWidth={2.5} />
                    </button>
                </div>

                {/* Search */}
                <div className="relative mb-6 group">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="w-4 h-4 text-gray-400 group-hover:text-[#0f6885] transition-colors" strokeWidth={2.5} />
                    </div>
                    <input
                        type="text"
                        className="w-full pl-11 pr-4 py-3.5 bg-white border border-gray-200 rounded-xl text-[14.5px] font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 placeholder-gray-400 transition-all shadow-sm group-hover:shadow-md"
                        placeholder="Search or start a new chat"
                    />
                </div>

                {/* Tabs */}
                <div className="flex space-x-1.5 overflow-x-auto pb-2 scrollbar-hide snap-x relative items-center">
                    {['Pickup', 'Recents', 'Awaiting Confirmation'].map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 rounded-full text-[13px] font-bold tracking-wide transition-all active:scale-95 snap-start shrink-0 ${activeTab === tab
                                ? 'bg-[#0f6885] text-white shadow-md mx-0.5'
                                : 'bg-transparent border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-800'
                                }`}
                        >
                            {tab}
                        </button>
                    ))}

                    {/* Add visual fade to indicate more tabs layout from original design */}
                    <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white to-transparent pointer-events-none"></div>
                </div>
            </div>

            {/* Chat List */}
            <div className="flex-1 overflow-y-auto pb-4 scrollbar-hide">
                {chats.map(chat => {
                    // Match visual styling exactly with the border selection
                    const isSelected = selectedChat?.id === chat.id || (chat.name === "StreetWearTn" && !selectedChat);

                    return (
                        <div
                            key={chat.id}
                            onClick={() => onSelectChat(chat)}
                            className={`flex items-center px-6 py-4 cursor-pointer relative transition-all duration-200 group border-l-[3px] ${isSelected
                                ? 'bg-transparent border-[#0f6885]'
                                : 'bg-transparent border-transparent hover:bg-gray-50'
                                }`}
                        >

                            {/* Avatar */}
                            <div className="relative mr-4 flex-shrink-0">
                                <img
                                    src={chat.avatar}
                                    alt={chat.name}
                                    className={`w-[50px] h-[50px] rounded-full object-cover transition-transform duration-300 ${isSelected ? 'scale-105 shadow-sm' : 'group-hover:scale-105 shadow-sm'}`}
                                />
                            </div>

                            {/* Chat Info */}
                            <div className="flex-1 min-w-0 pr-2">
                                <div className="flex justify-between items-center mb-1">
                                    <h3 className={`text-[15px] font-[800] truncate transition-colors text-gray-800 group-hover:text-black`}>
                                        {chat.name}
                                    </h3>
                                    <span className={`text-[12px] font-bold whitespace-nowrap transition-colors text-gray-400 group-hover:text-gray-500`}>
                                        {chat.time}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className={`text-[13.5px] truncate mr-2 font-[600] transition-colors ${(isSelected && chat.name === "StreetWearTn") ? 'text-gray-500' :
                                        chat.unread > 0 ? 'text-gray-600' : 'text-gray-400 group-hover:text-gray-500'
                                        }`}>
                                        {chat.lastMessage}
                                    </p>

                                    {chat.unread > 0 && (
                                        <div className="bg-[#ff6b2c] text-white text-[11px] font-black w-5 h-5 flex items-center justify-center rounded-full shadow-sm ml-auto shrink-0">
                                            {chat.unread}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default ChatList;
