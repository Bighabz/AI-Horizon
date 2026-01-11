'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { fetchStats } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    ArrowRight, Brain, Shield, Users, FileText,
    TrendingUp, Sparkles, Target, BookOpen,
    MessageSquare, Upload, ChevronRight
} from 'lucide-react';
import { StatsResponse } from '@/lib/types';

export default function HomePage() {
    const { data: stats } = useQuery<StatsResponse>({
        queryKey: ['stats'],
        queryFn: fetchStats,
    });

    return (
        <div className="space-y-16 pb-16">
            {/* Hero Section */}
            <section className="relative py-20 px-4 text-center overflow-hidden">
                {/* Background gradient */}
                <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent" />

                <div className="relative max-w-4xl mx-auto space-y-6">
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
                        <Sparkles className="h-4 w-4" />
                        NSF-Funded Research at CSUSB
                    </div>

                    <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
                        Educating into the{' '}
                        <span className="bg-gradient-to-r from-primary to-teal-400 bg-clip-text text-transparent">
                            AI Future
                        </span>
                    </h1>

                    <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                        Understand how AI is transforming cybersecurity careers. Explore evidence-based
                        research on which tasks will be replaced, augmented, or remain human-only.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
                        <Link href="/skills">
                            <Button size="lg" className="cursor-pointer w-full sm:w-auto">
                                Explore Skills Matrix
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                        </Link>
                        <Link href="/chat">
                            <Button size="lg" variant="outline" className="cursor-pointer w-full sm:w-auto">
                                <MessageSquare className="mr-2 h-5 w-5" />
                                Ask AI Assistant
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>

            {/* Stats Section */}
            <section className="container">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Card className="bg-card/50 border-primary/10">
                        <CardContent className="pt-6 text-center">
                            <div className="text-3xl md:text-4xl font-bold text-primary">
                                {stats?.total_tasks?.toLocaleString() || '1,350'}
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">DCWF Tasks Analyzed</p>
                        </CardContent>
                    </Card>
                    <Card className="bg-card/50 border-primary/10">
                        <CardContent className="pt-6 text-center">
                            <div className="text-3xl md:text-4xl font-bold text-primary">
                                {stats?.total_resources || 0}
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">Evidence Collected</p>
                        </CardContent>
                    </Card>
                    <Card className="bg-card/50 border-primary/10">
                        <CardContent className="pt-6 text-center">
                            <div className="text-3xl md:text-4xl font-bold text-primary">52</div>
                            <p className="text-sm text-muted-foreground mt-1">Work Roles Mapped</p>
                        </CardContent>
                    </Card>
                    <Card className="bg-card/50 border-primary/10">
                        <CardContent className="pt-6 text-center">
                            <div className="text-3xl md:text-4xl font-bold text-primary">4</div>
                            <p className="text-sm text-muted-foreground mt-1">Classification Types</p>
                        </CardContent>
                    </Card>
                </div>
            </section>

            {/* Classification Types */}
            <section className="container">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-bold mb-3">How AI Impacts Cybersecurity Roles</h2>
                    <p className="text-muted-foreground max-w-2xl mx-auto">
                        We classify each DCWF task based on how AI technology affects it
                    </p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card className="border-red-500/30 bg-red-500/5 hover:border-red-500/50 transition-colors cursor-pointer">
                        <CardHeader className="pb-2">
                            <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center mb-2">
                                <Target className="h-5 w-5 text-red-500" />
                            </div>
                            <CardTitle className="text-red-500">Replace</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                AI can fully automate this task with minimal human oversight. Confidence &gt;70%.
                            </CardDescription>
                        </CardContent>
                    </Card>

                    <Card className="border-amber-500/30 bg-amber-500/5 hover:border-amber-500/50 transition-colors cursor-pointer">
                        <CardHeader className="pb-2">
                            <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center mb-2">
                                <Users className="h-5 w-5 text-amber-500" />
                            </div>
                            <CardTitle className="text-amber-500">Augment</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                AI enhances human capabilities, improving speed and accuracy. Confidence 40-70%.
                            </CardDescription>
                        </CardContent>
                    </Card>

                    <Card className="border-emerald-500/30 bg-emerald-500/5 hover:border-emerald-500/50 transition-colors cursor-pointer">
                        <CardHeader className="pb-2">
                            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center mb-2">
                                <Shield className="h-5 w-5 text-emerald-500" />
                            </div>
                            <CardTitle className="text-emerald-500">Remain Human</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                Task requires human judgment, creativity, or ethical oversight. Confidence &lt;40%.
                            </CardDescription>
                        </CardContent>
                    </Card>

                    <Card className="border-blue-500/30 bg-blue-500/5 hover:border-blue-500/50 transition-colors cursor-pointer">
                        <CardHeader className="pb-2">
                            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center mb-2">
                                <Sparkles className="h-5 w-5 text-blue-500" />
                            </div>
                            <CardTitle className="text-blue-500">New Task</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <CardDescription>
                                AI creates entirely new responsibilities not in the original DCWF framework.
                            </CardDescription>
                        </CardContent>
                    </Card>
                </div>
            </section>

            {/* Features Grid */}
            <section className="container">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-bold mb-3">Research Tools</h2>
                    <p className="text-muted-foreground max-w-2xl mx-auto">
                        Everything you need to understand and prepare for the AI-augmented workforce
                    </p>
                </div>

                <div className="grid md:grid-cols-3 gap-6">
                    <Link href="/skills" className="group">
                        <Card className="h-full hover:border-primary/50 transition-all cursor-pointer group-hover:shadow-lg">
                            <CardHeader>
                                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
                                    <Brain className="h-6 w-6 text-primary" />
                                </div>
                                <CardTitle className="flex items-center justify-between">
                                    Skills Matrix
                                    <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription className="text-base">
                                    Explore DCWF work roles and see how AI impacts each one. Filter by category,
                                    role, and classification type.
                                </CardDescription>
                            </CardContent>
                        </Card>
                    </Link>

                    <Link href="/resources" className="group">
                        <Card className="h-full hover:border-primary/50 transition-all cursor-pointer group-hover:shadow-lg">
                            <CardHeader>
                                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
                                    <FileText className="h-6 w-6 text-primary" />
                                </div>
                                <CardTitle className="flex items-center justify-between">
                                    Evidence Library
                                    <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription className="text-base">
                                    Browse analyzed research papers, articles, and reports that inform our
                                    classifications.
                                </CardDescription>
                            </CardContent>
                        </Card>
                    </Link>

                    <Link href="/chat" className="group">
                        <Card className="h-full hover:border-primary/50 transition-all cursor-pointer group-hover:shadow-lg">
                            <CardHeader>
                                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
                                    <MessageSquare className="h-6 w-6 text-primary" />
                                </div>
                                <CardTitle className="flex items-center justify-between">
                                    AI Assistant
                                    <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <CardDescription className="text-base">
                                    Ask questions about career planning, skill development, and get personalized
                                    guidance for the AI era.
                                </CardDescription>
                            </CardContent>
                        </Card>
                    </Link>
                </div>
            </section>

            {/* CTA Section */}
            <section className="container">
                <Card className="bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border-primary/20">
                    <CardContent className="py-12 text-center">
                        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
                            <Upload className="h-8 w-8 text-primary" />
                        </div>
                        <h3 className="text-2xl font-bold mb-3">Contribute to the Research</h3>
                        <p className="text-muted-foreground max-w-lg mx-auto mb-6">
                            Found an article or research about AI in cybersecurity? Submit it to help build
                            our evidence base and improve classifications.
                        </p>
                        <Link href="/submit">
                            <Button size="lg" className="cursor-pointer">
                                Submit Evidence
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            </section>

            {/* About Section */}
            <section className="container">
                <div className="grid md:grid-cols-2 gap-8 items-center">
                    <div>
                        <h2 className="text-3xl font-bold mb-4">About This Research</h2>
                        <div className="space-y-4 text-muted-foreground">
                            <p>
                                AI Horizon is an NSF-funded research project at California State University,
                                San Bernardino (CSUSB) focused on understanding how artificial intelligence
                                is transforming the cybersecurity workforce.
                            </p>
                            <p>
                                Using the NICE Workforce Framework for Cybersecurity (DCWF), we analyze
                                over 1,350 tasks across 52 work roles to determine how AI will impact each one.
                            </p>
                            <p>
                                Our goal is to help cybersecurity professionals, students, and educators
                                prepare for the human-AI workforce of the future.
                            </p>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <Card className="bg-card/50">
                            <CardContent className="pt-6">
                                <TrendingUp className="h-8 w-8 text-primary mb-3" />
                                <h4 className="font-semibold mb-1">Evidence-Based</h4>
                                <p className="text-sm text-muted-foreground">
                                    Classifications backed by research and real-world data
                                </p>
                            </CardContent>
                        </Card>
                        <Card className="bg-card/50">
                            <CardContent className="pt-6">
                                <BookOpen className="h-8 w-8 text-primary mb-3" />
                                <h4 className="font-semibold mb-1">DCWF Aligned</h4>
                                <p className="text-sm text-muted-foreground">
                                    Built on the NICE cybersecurity framework
                                </p>
                            </CardContent>
                        </Card>
                        <Card className="bg-card/50">
                            <CardContent className="pt-6">
                                <Users className="h-8 w-8 text-primary mb-3" />
                                <h4 className="font-semibold mb-1">Career Focused</h4>
                                <p className="text-sm text-muted-foreground">
                                    Practical guidance for career planning
                                </p>
                            </CardContent>
                        </Card>
                        <Card className="bg-card/50">
                            <CardContent className="pt-6">
                                <Brain className="h-8 w-8 text-primary mb-3" />
                                <h4 className="font-semibold mb-1">AI-Powered</h4>
                                <p className="text-sm text-muted-foreground">
                                    Using Gemini for analysis and chat
                                </p>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </section>
        </div>
    );
}
