import React, { useState } from 'react';
import ChatList from '../../components/chat/ChatList';
import DashboardWelcome from '../../components/dashboard/DashboardWelcome';
import ActiveChat from '../../components/chat/ActiveChat';

const Inbox = () => {
    const [selectedChat, setSelectedChat] = useState(null);

    const [chats, setChats] = useState([]);

    // Handle starting a new chat from the dashboard
    const handleStartNewChat = (initialMessage) => {
        const now = new Date();
        const timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        const newChat = {
            id: Date.now(),
            name: 'AI Agent', // Default name for a new chat initiated from Dashboard
            lastMessage: `You: ${initialMessage}`,
            time: 'Just now',
            avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&q=80', // Temp AI Avatar
            unread: 0,
            initialMessageText: initialMessage, // Pass this so ActiveChat knows to render it first
            initialMessageTime: timeString
        };

        setChats([newChat, ...chats]);
        setSelectedChat(newChat);
    };

    // Handle updating an existing chat's last message
    const handleUpdateChat = (chatId, message, timeText) => {
        setChats(prevChats =>
            prevChats.map(chat =>
                chat.id === chatId
                    ? { ...chat, lastMessage: `You: ${message}`, time: timeText }
                    : chat
            )
        );
    };

    return (
        <div className="flex-1 flex overflow-hidden bg-[#fafafa]">
            {/* Search and Chat List Panel */}
            <ChatList
                chats={chats}
                selectedChat={selectedChat}
                onSelectChat={(chat) => setSelectedChat(chat)}
            />

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col relative overflow-hidden bg-[#fcfcfc]">
                {selectedChat ? (
                    <ActiveChat chat={selectedChat} onUpdateChat={handleUpdateChat} />
                ) : (
                    <DashboardWelcome onStartChat={handleStartNewChat} />
                )}
            </main>
        </div>
    );
};

export default Inbox;
