'use client';

import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { submitEvidence, api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useRouter } from 'next/navigation';
import {
    Loader2, AlertCircle, UploadCloud, FileType, CheckCircle2, Brain, Target,
    Lightbulb, ArrowRight, RotateCcw, Youtube, Newspaper, BookOpen, GraduationCap,
    TrendingUp, Award, Play, FileText, Globe, Sparkles
} from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getSessionId } from '@/lib/api';
import { SubmitResponse } from '@/lib/types';
import { ClassificationBadge } from '@/components/badges/ClassificationBadge';
import { Badge } from '@/components/ui/badge';

// Loading messages to show during classification
const LOADING_MESSAGES = [
    "Analyzing content...",
    "Extracting key insights...",
    "Mapping to DCWF framework...",
    "Evaluating AI impact...",
    "Generating classification..."
];

// Example content for each category
const EVIDENCE_EXAMPLES = [
    { icon: Youtube, text: "YouTube videos discussing AI trends in cybersecurity", color: "text-red-500" },
    { icon: Newspaper, text: "News articles about AI replacing security jobs", color: "text-blue-500" },
    { icon: TrendingUp, text: "Research papers on GPT for threat detection", color: "text-green-500" },
    { icon: Globe, text: "Industry reports on workforce transformation", color: "text-purple-500" },
];

const RESOURCE_EXAMPLES = [
    { icon: Youtube, text: "YouTube tutorials & certification prep videos", color: "text-red-500" },
    { icon: GraduationCap, text: "Online courses & bootcamp programs", color: "text-amber-500" },
    { icon: Award, text: "Certification training (CompTIA, CISSP, etc.)", color: "text-emerald-500" },
    { icon: BookOpen, text: "Educational platforms & learning paths", color: "text-cyan-500" },
];

export default function SubmitPage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState("url");
    const [url, setUrl] = useState('');
    const [content, setContent] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0]);
    const [result, setResult] = useState<SubmitResponse | null>(null);

    // Cycle through loading messages
    const startLoadingAnimation = () => {
        let index = 0;
        const interval = setInterval(() => {
            index = (index + 1) % LOADING_MESSAGES.length;
            setLoadingMessage(LOADING_MESSAGES[index]);
        }, 2000);
        return interval;
    };

    // Mutation for URL/Text
    const submitMutation = useMutation({
        mutationFn: submitEvidence,
        onMutate: () => {
            setResult(null);
            const interval = startLoadingAnimation();
            return { interval };
        },
        onSuccess: (data, _vars, context) => {
            clearInterval(context?.interval);
            setResult(data);
        },
        onError: (_err, _vars, context) => {
            clearInterval(context?.interval);
        }
    });

    // Mutation for File
    const uploadMutation = useMutation({
        mutationFn: async (fileToUpload: File) => {
            const formData = new FormData();
            formData.append('file', fileToUpload);
            formData.append('session_id', getSessionId());

            const { data } = await api.post('/api/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return data;
        },
        onMutate: () => {
            setResult(null);
            const interval = startLoadingAnimation();
            return { interval };
        },
        onSuccess: (data, _vars, context) => {
            clearInterval(context?.interval);
            setResult(data);
        },
        onError: (_err, _vars, context) => {
            clearInterval(context?.interval);
        }
    });

    const resetForm = () => {
        setResult(null);
        setUrl('');
        setContent('');
        setFile(null);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (activeTab === "url" && url) {
            submitMutation.mutate({ url });
        } else if (activeTab === "text" && content) {
            submitMutation.mutate({ content });
        } else if (activeTab === "file" && file) {
            uploadMutation.mutate(file);
        }
    };

    const handleFileDrop = (e: React.DragEvent) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) setFile(droppedFile);
    };

    const isPending = submitMutation.isPending || uploadMutation.isPending;
    const isError = submitMutation.isError || uploadMutation.isError;
    const error = submitMutation.error || uploadMutation.error;

    // Show duplicate content result
    if (result && result.is_duplicate === true) {
        return (
            <div className="max-w-3xl mx-auto py-8 space-y-6">
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/10 mb-4">
                        <AlertCircle className="h-8 w-8 text-blue-500" />
                    </div>
                    <h1 className="text-3xl font-bold">Duplicate Content</h1>
                    <p className="text-muted-foreground">
                        This content has already been submitted and analyzed.
                    </p>
                </div>

                <Card className="border-2 border-blue-500/20">
                    <CardContent className="py-6 space-y-4">
                        <Alert className="border-blue-500/30 bg-blue-500/5">
                            <AlertCircle className="h-4 w-4 text-blue-500" />
                            <AlertTitle>Already in Database</AlertTitle>
                            <AlertDescription>
                                {result.message || "This URL or content was previously submitted. No duplicate entry was created."}
                            </AlertDescription>
                        </Alert>
                        {result.classification && (
                            <div className="text-center pt-4 border-t">
                                <p className="text-sm text-muted-foreground mb-2">Previous Classification</p>
                                <ClassificationBadge
                                    type={result.classification.classification as "Replace" | "Augment" | "Remain Human" | "New Task"}
                                    className="text-lg px-6 py-2"
                                />
                            </div>
                        )}
                    </CardContent>
                </Card>

                <div className="flex flex-col sm:flex-row gap-3">
                    <Button onClick={resetForm} variant="outline" className="flex-1">
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Submit Different Content
                    </Button>
                    <Button
                        onClick={() => router.push('/resources')}
                        className="flex-1"
                    >
                        View Evidence Library
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                </div>
            </div>
        );
    }

    // Show irrelevant content result
    if (result && result.is_relevant === false) {
        return (
            <div className="max-w-3xl mx-auto py-8 space-y-6">
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-500/10 mb-4">
                        <AlertCircle className="h-8 w-8 text-amber-500" />
                    </div>
                    <h1 className="text-3xl font-bold">Content Not Relevant</h1>
                    <p className="text-muted-foreground">
                        This content doesn't appear to be related to cybersecurity or DCWF tasks.
                    </p>
                </div>

                <Card className="border-2 border-amber-500/20">
                    <CardContent className="py-6 space-y-4">
                        <div className="text-center">
                            <p className="text-sm text-muted-foreground mb-2">Relevance Score</p>
                            <div className="text-2xl font-bold text-amber-500">
                                {Math.round((result.relevance_score || 0) * 100)}%
                            </div>
                        </div>
                        {result.relevance_reason && (
                            <p className="text-sm text-center text-muted-foreground">
                                {result.relevance_reason}
                            </p>
                        )}
                        <Alert>
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Not Stored</AlertTitle>
                            <AlertDescription>
                                This content was analyzed but not added to the knowledge base because it doesn't relate to cybersecurity workforce topics.
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                </Card>

                <div className="flex flex-col sm:flex-row gap-3">
                    <Button onClick={resetForm} variant="outline" className="flex-1">
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Try Different Content
                    </Button>
                </div>
            </div>
        );
    }

    // Show results view if we have a result
    if (result && result.success && result.classification) {
        const cls = result.classification;
        const isResource = result.classification.submission_type === 'resource';

        return (
            <div className="max-w-3xl mx-auto py-8 space-y-6">
                {/* Success Header */}
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10 mb-4">
                        <CheckCircle2 className="h-8 w-8 text-green-500" />
                    </div>
                    <h1 className="text-3xl font-bold">Analysis Complete</h1>
                    <p className="text-muted-foreground">
                        {isResource
                            ? "Your learning resource has been added to the Learning Library."
                            : "Your evidence has been classified and added to the Evidence Library."
                        }
                    </p>
                    <Badge variant="outline" className="mt-2">
                        {isResource ? "Learning Resource" : "Evidence"}
                    </Badge>
                </div>

                {/* Classification Result Card */}
                <Card className="border-2 border-primary/20">
                    <CardHeader className="text-center pb-2">
                        <CardDescription>AI Impact Classification</CardDescription>
                        <div className="flex justify-center mt-2">
                            <ClassificationBadge
                                type={cls.classification as "Replace" | "Augment" | "Remain Human" | "New Task"}
                                className="text-lg px-6 py-2"
                            />
                        </div>
                        <div className="text-sm text-muted-foreground mt-2">
                            {Math.round(cls.confidence * 100)}% Confidence
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Rationale */}
                        <div className="space-y-2">
                            <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                                <Brain className="h-4 w-4" />
                                Analysis Summary
                            </div>
                            <p className="text-sm leading-relaxed">{cls.rationale}</p>
                        </div>

                        {/* DCWF Tasks */}
                        {cls.dcwf_tasks && cls.dcwf_tasks.length > 0 && (
                            <div className="space-y-3">
                                <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                                    <Target className="h-4 w-4" />
                                    Related DCWF Tasks
                                </div>
                                <div className="space-y-2">
                                    {cls.dcwf_tasks.slice(0, 5).map((task, i) => (
                                        <div key={i} className="p-3 rounded-lg bg-secondary/50 border border-border/50">
                                            <div className="flex items-start justify-between gap-2">
                                                <div>
                                                    <Badge variant="outline" className="mb-1">{task.task_id}</Badge>
                                                    <p className="text-sm font-medium">{task.task_name}</p>
                                                </div>
                                            </div>
                                            {task.impact_description && (
                                                <p className="text-xs text-muted-foreground mt-2">{task.impact_description}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Key Findings */}
                        {cls.key_findings && cls.key_findings.length > 0 && (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                                    <Lightbulb className="h-4 w-4" />
                                    Key Findings
                                </div>
                                <ul className="space-y-1">
                                    {cls.key_findings.map((finding, i) => (
                                        <li key={i} className="text-sm flex items-start gap-2">
                                            <span className="text-primary mt-1">•</span>
                                            <span>{finding}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Work Roles */}
                        {cls.work_roles && cls.work_roles.length > 0 && (
                            <div className="space-y-2">
                                <div className="text-sm font-semibold text-muted-foreground">Relevant Work Roles</div>
                                <div className="flex flex-wrap gap-2">
                                    {cls.work_roles.map((role, i) => (
                                        <Badge key={i} variant="secondary">{role}</Badge>
                                    ))}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-3">
                    <Button onClick={resetForm} variant="outline" className="flex-1">
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Submit Another
                    </Button>
                    <Button
                        onClick={() => router.push(isResource ? '/resources?submission_type=resource' : '/resources?submission_type=evidence')}
                        className="flex-1"
                    >
                        View {isResource ? 'Learning Library' : 'Evidence Library'}
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto py-8 space-y-8">
            {/* Hero Section */}
            <div className="text-center space-y-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
                    <Sparkles className="h-4 w-4" />
                    AI-Powered Analysis
                </div>
                <h1 className="text-4xl font-bold tracking-tight">
                    Contribute to the Research
                </h1>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                    Submit articles, YouTube videos, courses, or certifications. Our AI automatically
                    classifies content and maps it to DCWF work roles.
                </p>
            </div>

            {/* What to Submit - Two Cards */}
            <div className="grid md:grid-cols-2 gap-6">
                {/* Evidence Card */}
                <Card className="border-2 hover:border-blue-500/50 transition-colors group">
                    <CardHeader className="pb-4">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                                <TrendingUp className="h-6 w-6 text-blue-500" />
                            </div>
                            <div>
                                <CardTitle className="text-lg">Evidence & Research</CardTitle>
                                <CardDescription>AI impact on cybersecurity</CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Content that shows how AI is changing the cybersecurity workforce - news, research, expert opinions.
                        </p>
                        <div className="space-y-3">
                            {EVIDENCE_EXAMPLES.map((item, i) => (
                                <div key={i} className="flex items-center gap-3 text-sm">
                                    <item.icon className={`h-4 w-4 ${item.color}`} />
                                    <span>{item.text}</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Learning Resources Card */}
                <Card className="border-2 hover:border-emerald-500/50 transition-colors group">
                    <CardHeader className="pb-4">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                                <GraduationCap className="h-6 w-6 text-emerald-500" />
                            </div>
                            <div>
                                <CardTitle className="text-lg">Learning Resources</CardTitle>
                                <CardDescription>Education & certifications</CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Educational content to help people build cybersecurity skills - courses, tutorials, certifications.
                        </p>
                        <div className="space-y-3">
                            {RESOURCE_EXAMPLES.map((item, i) => (
                                <div key={i} className="flex items-center gap-3 text-sm">
                                    <item.icon className={`h-4 w-4 ${item.color}`} />
                                    <span>{item.text}</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* YouTube Emphasis Banner */}
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-red-500/10 via-red-500/5 to-transparent border border-red-500/20 p-6">
                <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-red-500/10 flex items-center justify-center shrink-0">
                        <Play className="h-7 w-7 text-red-500 ml-1" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg flex items-center gap-2">
                            <Youtube className="h-5 w-5 text-red-500" />
                            YouTube Videos Welcome
                        </h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Paste any YouTube link - we'll extract and analyze the video content automatically.
                            Both educational tutorials and news/discussion videos are accepted.
                        </p>
                    </div>
                </div>
            </div>

            {/* Loading State */}
            {isPending && (
                <Card className="border-primary/30 bg-primary/5">
                    <CardContent className="py-12 text-center">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                            <Loader2 className="h-8 w-8 text-primary animate-spin" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">{loadingMessage}</h3>
                        <p className="text-sm text-muted-foreground">
                            This may take 10-30 seconds depending on content length.
                        </p>
                        <div className="flex justify-center gap-1 mt-4">
                            {LOADING_MESSAGES.map((_, i) => (
                                <div
                                    key={i}
                                    className={`w-2 h-2 rounded-full transition-colors ${
                                        LOADING_MESSAGES[i] === loadingMessage ? 'bg-primary' : 'bg-muted'
                                    }`}
                                />
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Submit Form */}
            <Card className={`border-2 ${isPending ? 'opacity-50 pointer-events-none' : ''}`}>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Brain className="h-5 w-5 text-primary" />
                        Submit Content for Analysis
                    </CardTitle>
                    <CardDescription>
                        Our AI will automatically detect whether it's evidence or a learning resource.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                        <TabsList className="grid w-full grid-cols-3 mb-6">
                            <TabsTrigger value="url" className="gap-2">
                                <Globe className="h-4 w-4" />
                                URL / Link
                            </TabsTrigger>
                            <TabsTrigger value="file" className="gap-2">
                                <UploadCloud className="h-4 w-4" />
                                File Upload
                            </TabsTrigger>
                            <TabsTrigger value="text" className="gap-2">
                                <FileText className="h-4 w-4" />
                                Paste Text
                            </TabsTrigger>
                        </TabsList>

                        <form onSubmit={handleSubmit} className="space-y-6">
                            {isError && (
                                <Alert variant="destructive">
                                    <AlertCircle className="h-4 w-4" />
                                    <AlertTitle>Error</AlertTitle>
                                    <AlertDescription>
                                        {error instanceof Error ? error.message : "Failed to submit content."}
                                    </AlertDescription>
                                </Alert>
                            )}

                            <TabsContent value="url" className="space-y-4 mt-0">
                                <div className="space-y-3">
                                    <Label htmlFor="url" className="text-base">Enter URL</Label>
                                    <Input
                                        id="url"
                                        placeholder="https://youtube.com/watch?v=... or any article URL"
                                        value={url}
                                        onChange={(e) => setUrl(e.target.value)}
                                        disabled={isPending}
                                        className="h-12 text-base"
                                    />
                                    <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                                        <Badge variant="secondary" className="font-normal">YouTube</Badge>
                                        <Badge variant="secondary" className="font-normal">News Articles</Badge>
                                        <Badge variant="secondary" className="font-normal">Research Papers</Badge>
                                        <Badge variant="secondary" className="font-normal">Course Pages</Badge>
                                        <Badge variant="secondary" className="font-normal">Blog Posts</Badge>
                                    </div>
                                </div>
                            </TabsContent>

                            <TabsContent value="file" className="space-y-4 mt-0">
                                <div
                                    className={`
                                        border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer
                                        ${file ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50'}
                                    `}
                                    onDragOver={(e) => e.preventDefault()}
                                    onDrop={handleFileDrop}
                                    onClick={() => !file && document.getElementById('file-upload')?.click()}
                                >
                                    {file ? (
                                        <div className="flex flex-col items-center">
                                            <FileType className="h-12 w-12 text-primary mb-3" />
                                            <p className="font-semibold text-lg">{file.name}</p>
                                            <p className="text-sm text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="mt-3 text-destructive hover:text-destructive"
                                                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                                            >
                                                Remove File
                                            </Button>
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center">
                                            <UploadCloud className="h-12 w-12 text-muted-foreground mb-4" />
                                            <p className="font-semibold text-lg">Drop a file here or click to browse</p>
                                            <p className="text-sm text-muted-foreground mt-2">PDF, DOCX, or TXT up to 10MB</p>
                                            <input
                                                id="file-upload"
                                                type="file"
                                                className="hidden"
                                                accept=".pdf,.docx,.txt"
                                                onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
                                            />
                                        </div>
                                    )}
                                </div>
                            </TabsContent>

                            <TabsContent value="text" className="space-y-4 mt-0">
                                <div className="space-y-3">
                                    <Label htmlFor="content" className="text-base">Paste Content</Label>
                                    <Textarea
                                        id="content"
                                        placeholder="Paste article text, research findings, or course description here..."
                                        className="min-h-[200px] text-base"
                                        value={content}
                                        onChange={(e) => setContent(e.target.value)}
                                        disabled={isPending}
                                    />
                                </div>
                            </TabsContent>

                            <Button type="submit" size="lg" className="w-full" disabled={isPending}>
                                {isPending ? (
                                    <>
                                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <Brain className="mr-2 h-5 w-5" />
                                        Analyze with AI
                                    </>
                                )}
                            </Button>
                        </form>
                    </Tabs>
                </CardContent>
            </Card>

            {/* How it Works */}
            <div className="grid md:grid-cols-3 gap-4 pt-4">
                <div className="text-center p-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3 text-primary font-bold">1</div>
                    <h4 className="font-semibold mb-1">Submit Content</h4>
                    <p className="text-sm text-muted-foreground">Paste a URL, upload a file, or paste text directly</p>
                </div>
                <div className="text-center p-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3 text-primary font-bold">2</div>
                    <h4 className="font-semibold mb-1">AI Analyzes</h4>
                    <p className="text-sm text-muted-foreground">Gemini extracts key insights and maps to DCWF tasks</p>
                </div>
                <div className="text-center p-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3 text-primary font-bold">3</div>
                    <h4 className="font-semibold mb-1">Added to Library</h4>
                    <p className="text-sm text-muted-foreground">Content is classified and added to our knowledge base</p>
                </div>
            </div>
        </div>
    );
}
