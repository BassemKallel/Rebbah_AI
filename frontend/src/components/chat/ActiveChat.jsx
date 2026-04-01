import React, { useState, useRef, useEffect } from 'react';
import TopActionBar from './TopActionBar';
import ChatInput from './ChatInput';
import MessageBubble from './MessageBubble';

const ActiveChat = ({ chat, onUpdateChat }) => {

    // Initialize state with default mock messages
    const defaultMessages = [];

    // Check if we are opening a brand new chat spawned from the Dashboard
    const initialMessages = chat?.initialMessageText ? [
        {
            id: 1,
            sender: 'user',
            text: chat.initialMessageText,
            time: chat.initialMessageTime
        }
    ] : defaultMessages;

    // Notice we re-initialize state if the chat ID changes. 
    // This allows clicking between different chats to "reset" the view.
    const [messages, setMessages] = useState(initialMessages);

    // Reset messages when the chat object changes
    useEffect(() => {
        if (chat?.initialMessageText) {
            setMessages([
                {
                    id: 1,
                    sender: 'user',
                    text: chat.initialMessageText,
                    time: chat.initialMessageTime
                }
            ]);

            // Readiness for backend population via webhook integration
        } else {
            setMessages(defaultMessages);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [chat.id]);


    const messagesEndRef = useRef(null);

    // Auto-scroll to bottom whenever messages array changes
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = (text) => {
        const now = new Date();
        const timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        // Append new message from user
        const newUserMsg = {
            id: Date.now(),
            sender: 'user',
            text: text,
            time: timeString
        };

        setMessages(prev => [...prev, newUserMsg]);

        // Trigger side-effect to update Inbox chat preview
        if (onUpdateChat) {
            onUpdateChat(chat.id, text, timeString);
        }

        // Signal update to parent for backend parity
        if (onUpdateChat) {
            onUpdateChat(chat.id, text, timeString);
        }
    };

    return (
        <div className="flex-1 flex flex-col relative w-full h-full bg-white border border-gray-100 shadow-sm rounded-2xl m-4 overflow-hidden">

            {/* Main content Area - Redundant Topbar Removed */}

            {/* Messages area wrapper. 
          Use overflow-y-auto here to push the input down only to the bottom of the container,
          but keep scrolling confined to the chat history itself. */}
            <div className="flex-1 flex flex-col px-4 md:px-12 w-full max-w-5xl mx-auto overflow-hidden">

                {/* Date Badge */}
                <div className="w-full flex justify-center py-2 my-5 shrink-0 transition-opacity">
                    <div className="bg-[#6b7280] text-white text-[12.5px] tracking-wide font-bold px-4 py-1.5 rounded-full shadow-sm hover:shadow-md hover:bg-gray-600 transition-all cursor-default relative overflow-hidden group">
                        <span className="relative z-10">Today</span>
                        <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 pointer-events-none"></div>
                    </div>
                </div>

                {/* Chat History scrollable area */}
                <div className="flex-1 overflow-y-auto pr-2 pb-4 scroll-smooth scrollbar-hide flex flex-col">
                    {messages.map((msg) => (
                        <MessageBubble key={msg.id} message={msg} />
                    ))}
                    {/* Invisible div used to anchor scrolling to bottom */}
                    <div ref={messagesEndRef} className="h-4 shrink-0"></div>
                </div>

                {/* Chat Input remains sticky at the bottom */}
                <div className="shrink-0 pb-4 pt-2 bg-[#fcfcfc]">
                    <ChatInput onSendMessage={handleSendMessage} />
                </div>
            </div>
        </div>
    );
};

export default ActiveChat;
