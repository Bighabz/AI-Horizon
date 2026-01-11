'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { sendChatMessage, getSessionId } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
    Send, User, Bot, ExternalLink,
    GraduationCap, Target, Lightbulb, BookOpen,
    TrendingUp, HelpCircle, Sparkles
} from 'lucide-react';
import { ChatResponse } from '@/lib/types';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    sources?: { title: string; url: string; relevance?: number }[];
}

// Simple markdown-like formatting for chat messages
function formatMessage(content: string): React.ReactNode {
    // Split into sections by headers
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let currentList: string[] = [];

    const flushList = () => {
        if (currentList.length > 0) {
            elements.push(
                <ul key={`list-${elements.length}`} className="space-y-1.5 my-2">
                    {currentList.map((item, i) => (
                        <li key={i} className="flex items-start gap-2">
                            <span className="text-primary mt-0.5">•</span>
                            <span>{item}</span>
                        </li>
                    ))}
                </ul>
            );
            currentList = [];
        }
    };

    lines.forEach((line, i) => {
        const trimmed = line.trim();

        // Headers with emojis (like **📋 Summary**)
        if (trimmed.match(/^\*\*[📋🎯📊💡🔗].+\*\*:?$/)) {
            flushList();
            const headerText = trimmed.replace(/^\*\*/, '').replace(/\*\*:?$/, '');
            elements.push(
                <h3 key={i} className="font-bold text-base mt-4 mb-2 flex items-center gap-2 text-primary">
                    {headerText}
                </h3>
            );
        }
        // Bold text sections
        else if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
            flushList();
            const text = trimmed.slice(2, -2);
            elements.push(
                <p key={i} className="font-semibold mt-3 mb-1">{text}</p>
            );
        }
        // List items
        else if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
            currentList.push(trimmed.slice(2));
        }
        // Numbered list items
        else if (trimmed.match(/^\d+\.\s/)) {
            currentList.push(trimmed.replace(/^\d+\.\s/, ''));
        }
        // Task IDs (like **A.0004**: ...)
        else if (trimmed.match(/^\*\*[A-Z0-9.-]+\*\*:/)) {
            flushList();
            const match = trimmed.match(/^\*\*([A-Z0-9.-]+)\*\*:\s*(.+)/);
            if (match) {
                elements.push(
                    <div key={i} className="p-2.5 my-2 rounded-lg bg-secondary/50 border border-border/50">
                        <div className="flex items-start gap-2">
                            <Badge variant="outline" className="shrink-0 mt-0.5">{match[1]}</Badge>
                            <span className="text-sm">{match[2]}</span>
                        </div>
                    </div>
                );
            }
        }
        // Regular paragraph
        else if (trimmed.length > 0) {
            flushList();
            // Handle inline bold
            const formatted = trimmed.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            elements.push(
                <p key={i} className="my-1.5" dangerouslySetInnerHTML={{ __html: formatted }} />
            );
        }
        // Empty line
        else {
            flushList();
        }
    });

    flushList();
    return <div className="space-y-1">{elements}</div>;
}

export default function ChatPage() {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: `Welcome to the AI Horizon Research Assistant! I'm here to help you navigate the changing landscape of cybersecurity careers in the age of AI.

**What I can help you with:**
* Explore how AI is impacting specific DCWF work roles and tasks
* Find evidence and research on AI automation in cybersecurity
* Understand which skills are becoming more or less valuable
* Create personalized career development plans
* Generate practice quizzes to test your knowledge

**Try asking me:**
* "How will AI affect the Security Analyst role?"
* "What skills should I develop to stay relevant?"
* "Create a quiz on threat detection fundamentals"
* "Help me build a career plan for transitioning to AI-augmented security"`
        }
    ]);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Initialize session
    useEffect(() => {
        getSessionId();
    }, []);

    const mutation = useMutation({
        mutationFn: sendChatMessage,
        onSuccess: (data: ChatResponse) => {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.output,
                sources: data.sources.map(url => ({ title: '', url, relevance: 1 }))
            }]);
        },
        onError: () => {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
        }
    });

    const handleSend = (messageText?: string) => {
        const text = messageText || input;
        if (!text.trim()) return;

        setMessages(prev => [...prev, { role: 'user', content: text }]);
        setInput('');
        mutation.mutate(text);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        handleSend();
    };

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    // Career-focused quick actions
    const QUICK_ACTIONS = [
        { icon: TrendingUp, label: 'Career Impact', query: 'How is AI changing the cybersecurity job market? What roles are growing vs declining?' },
        { icon: Target, label: 'My Role', query: 'Analyze the Security Analyst role - what tasks will AI replace vs augment?' },
        { icon: GraduationCap, label: 'Skill Building', query: 'What skills should I develop to thrive in AI-augmented cybersecurity?' },
        { icon: BookOpen, label: 'Practice Quiz', query: 'Create a 5-question quiz to test my knowledge of AI in cybersecurity operations.' },
        { icon: Lightbulb, label: 'Career Plan', query: 'Help me create a career development plan for transitioning to AI-augmented security work.' },
        { icon: HelpCircle, label: 'DCWF Explained', query: 'Explain the DCWF framework and how it categorizes cybersecurity work roles.' },
    ];

    const FOLLOW_UP_SUGGESTIONS = [
        'What certifications should I pursue?',
        'Show me evidence for this claim',
        'How do I prepare for this transition?',
        'Give me a practice scenario',
    ];

    return (
        <div className="flex h-[calc(100vh-8rem)] gap-4">
            {/* Sidebar - Quick Actions */}
            <div className="hidden lg:flex flex-col w-72 space-y-4">
                <Card className="bg-card/50 border-primary/10">
                    <CardContent className="py-4">
                        <h3 className="font-semibold mb-4 flex items-center text-sm">
                            <Sparkles className="mr-2 h-4 w-4 text-primary" />
                            Quick Actions
                        </h3>
                        <div className="space-y-2">
                            {QUICK_ACTIONS.map((action, i) => (
                                <Button
                                    key={i}
                                    variant="ghost"
                                    className="w-full justify-start text-sm h-auto py-2.5 px-3 hover:bg-primary/10"
                                    onClick={() => handleSend(action.query)}
                                    disabled={mutation.isPending}
                                >
                                    <action.icon className="mr-2 h-4 w-4 text-primary shrink-0" />
                                    {action.label}
                                </Button>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Tips Card */}
                <Card className="bg-gradient-to-br from-primary/5 to-accent/5 border-primary/10">
                    <CardContent className="py-4">
                        <h3 className="font-semibold mb-2 text-sm flex items-center">
                            <Lightbulb className="mr-2 h-4 w-4 text-amber-500" />
                            Pro Tip
                        </h3>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                            Ask me to create a personalized career roadmap based on your current role
                            and where you want to be in 2-3 years!
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Chat Area */}
            <Card className="flex-1 flex flex-col shadow-sm border-primary/10">
                <CardContent className="flex-1 p-0 flex flex-col h-full">
                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-6">
                        {messages.map((msg, i) => (
                            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                    <Avatar className={`h-8 w-8 shrink-0 ${msg.role === 'assistant' ? 'bg-primary/10' : 'bg-secondary'}`}>
                                        <AvatarFallback>
                                            {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-primary" />}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="space-y-2">
                                        <div className={`p-4 rounded-xl text-sm ${
                                            msg.role === 'user'
                                                ? 'bg-primary text-primary-foreground'
                                                : 'bg-muted/50 border border-border/50'
                                        }`}>
                                            {msg.role === 'user' ? msg.content : formatMessage(msg.content)}
                                        </div>

                                        {/* Sources */}
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="px-2">
                                                <span className="text-xs text-muted-foreground font-semibold">Sources:</span>
                                                <div className="flex flex-wrap gap-2 mt-1">
                                                    {msg.sources.slice(0, 3).map((source, idx) => (
                                                        <a
                                                            key={idx}
                                                            href={source.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-secondary/50 text-teal-400 hover:bg-secondary transition-colors"
                                                        >
                                                            <ExternalLink className="h-3 w-3" />
                                                            {new URL(source.url).hostname.replace('www.', '').slice(0, 20)}
                                                        </a>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Follow-up suggestions after assistant messages */}
                                        {msg.role === 'assistant' && i === messages.length - 1 && !mutation.isPending && i > 0 && (
                                            <div className="flex flex-wrap gap-2 mt-2 px-2">
                                                {FOLLOW_UP_SUGGESTIONS.map((suggestion, idx) => (
                                                    <Button
                                                        key={idx}
                                                        variant="outline"
                                                        size="sm"
                                                        className="text-xs h-7 px-2 border-dashed"
                                                        onClick={() => handleSend(suggestion)}
                                                    >
                                                        {suggestion}
                                                    </Button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {/* Typing indicator */}
                        {mutation.isPending && (
                            <div className="flex justify-start">
                                <div className="flex gap-3">
                                    <Avatar className="h-8 w-8 bg-primary/10">
                                        <AvatarFallback><Bot className="h-4 w-4 text-primary" /></AvatarFallback>
                                    </Avatar>
                                    <div className="bg-muted/50 border border-border/50 p-4 rounded-xl">
                                        <div className="flex items-center gap-2">
                                            <div className="flex gap-1">
                                                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                            </div>
                                            <span className="text-sm text-muted-foreground ml-2">Researching...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={scrollRef} />
                    </div>

                    {/* Mobile Quick Actions */}
                    <div className="lg:hidden px-4 py-2 border-t bg-muted/30 overflow-x-auto">
                        <div className="flex gap-2">
                            {QUICK_ACTIONS.slice(0, 4).map((action, i) => (
                                <Button
                                    key={i}
                                    variant="outline"
                                    size="sm"
                                    className="shrink-0 text-xs"
                                    onClick={() => handleSend(action.query)}
                                    disabled={mutation.isPending}
                                >
                                    <action.icon className="mr-1 h-3 w-3" />
                                    {action.label}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* Input */}
                    <div className="p-4 border-t bg-background">
                        <form onSubmit={handleSubmit} className="flex gap-2">
                            <Input
                                placeholder="Ask about AI impact, career planning, or request a practice quiz..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                disabled={mutation.isPending}
                                className="bg-muted/30"
                            />
                            <Button type="submit" size="icon" disabled={mutation.isPending || !input.trim()}>
                                <Send className="h-4 w-4" />
                            </Button>
                        </form>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
