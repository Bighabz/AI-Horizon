'use client';

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FilterX } from "lucide-react";
import { SearchResult } from '@/lib/types';

interface CascadeFilterProps {
    onFilterChange: (filters: FilterState) => void;
}

export interface FilterState {
    category: string;
    role: string;
    taskId: string;
    classifications: string[];
}

export function CascadeFilter({ onFilterChange }: CascadeFilterProps) {
    // State
    const [selectedCategory, setSelectedCategory] = useState<string>("All");
    const [selectedRole, setSelectedRole] = useState<string>("All");
    const [selectedTask, setSelectedTask] = useState<string>("All");
    const [selectedClassifications, setSelectedClassifications] = useState<string[]>([]);

    // 1. Fetch Roles (Source for Categories & Roles)
    const { data: roles = [], isLoading: isLoadingRoles } = useQuery({
        queryKey: ['roles'],
        queryFn: async () => {
            const { data } = await api.get<{ roles: Array<{ id: string, name: string, category: string }> }>('/api/roles');
            return data.roles;
        }
    });

    // 2. Fetch Tasks when Role is selected
    const { data: tasks = [], isLoading: isLoadingTasks } = useQuery({
        queryKey: ['tasks', selectedRole],
        queryFn: async () => {
            if (selectedRole === "All") return [];
            const { data } = await api.get<{ results: SearchResult[] }>('/api/search', {
                params: { job_role: selectedRole }
            });
            return data.results;
        },
        enabled: selectedRole !== "All"
    });

    // Derived Data: Categories
    const categories = React.useMemo(() => {
        const cats = new Set<string>(["All"]);
        roles.forEach(r => cats.add(r.category));
        return Array.from(cats).sort();
    }, [roles]);

    // Derived Data: Filtered Roles based on Category
    const filteredRoles = React.useMemo(() => {
        if (selectedCategory === "All") return roles;
        return roles.filter(r => r.category === selectedCategory);
    }, [roles, selectedCategory]);

    // Effect: Propagate changes
    useEffect(() => {
        onFilterChange({
            category: selectedCategory,
            role: selectedRole,
            taskId: selectedTask,
            classifications: selectedClassifications
        });
    }, [selectedCategory, selectedRole, selectedTask, selectedClassifications, onFilterChange]);

    // Handlers
    const toggleClassification = (cls: string) => {
        setSelectedClassifications(prev =>
            prev.includes(cls) ? prev.filter(c => c !== cls) : [...prev, cls]
        );
    };

    const clearFilters = () => {
        setSelectedCategory("All");
        setSelectedRole("All");
        setSelectedTask("All");
        setSelectedClassifications([]);
    };

    return (
        <Card className="mb-8 border-primary/20 bg-card/50 backdrop-blur">
            <CardContent className="pt-4 sm:pt-6 space-y-4 sm:space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-6">

                    {/* 1. Category */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">DCWF Category</label>
                        <Select value={selectedCategory} onValueChange={(val) => {
                            setSelectedCategory(val);
                            setSelectedRole("All"); // Reset downstream
                            setSelectedTask("All");
                        }}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select Category" />
                            </SelectTrigger>
                            <SelectContent>
                                {categories.map(c => (
                                    <SelectItem key={c} value={c}>{c}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* 2. Work Role */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">Work Role</label>
                        <Select
                            value={selectedRole}
                            onValueChange={(val) => {
                                setSelectedRole(val);
                                setSelectedTask("All");
                            }}
                            disabled={isLoadingRoles}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select Role" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="All">All Roles</SelectItem>
                                {filteredRoles.map(r => (
                                    <SelectItem key={r.id} value={r.name}>{r.name} ({r.id})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* 3. DCWF Task */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">DCWF Task</label>
                        <Select
                            value={selectedTask}
                            onValueChange={setSelectedTask}
                            disabled={selectedRole === "All" || isLoadingTasks}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select Task" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="All">All Tasks</SelectItem>
                                {tasks.map(t => (
                                    <SelectItem key={t.task_id} value={t.task_id}>{t.task_id} - {t.task_name.substring(0, 40)}...</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                {/* 4. Classification Chips */}
                <div className="space-y-3 pt-2 border-t border-border/50">
                    <div className="flex justify-between items-center">
                        <label className="text-sm font-medium text-muted-foreground">Filter by Classification</label>
                        {(selectedCategory !== "All" || selectedRole !== "All" || selectedTask !== "All" || selectedClassifications.length > 0) && (
                            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-auto p-0 text-muted-foreground hover:text-white">
                                <FilterX className="h-3 w-3 mr-1" /> Reset
                            </Button>
                        )}
                    </div>
                    <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2 sm:gap-3">
                        {[
                            { label: "Replace", color: "border-red-500 text-red-500", active: "bg-red-500/20" },
                            { label: "Augment", color: "border-amber-500 text-amber-500", active: "bg-amber-500/20" },
                            { label: "Remain Human", color: "border-emerald-500 text-emerald-500", active: "bg-emerald-500/20" },
                            { label: "New Task", color: "border-blue-500 text-blue-500", active: "bg-blue-500/20" }
                        ].map((opt) => {
                            const isSelected = selectedClassifications.includes(opt.label);
                            return (
                                <button
                                    key={opt.label}
                                    onClick={() => toggleClassification(opt.label)}
                                    className={`
                                        px-3 sm:px-4 py-2 sm:py-1.5 rounded-full border text-xs sm:text-sm font-medium transition-all
                                        ${opt.color}
                                        ${isSelected ? opt.active + " shadow-sm ring-1 ring-offset-1 ring-offset-background " + opt.color.split(' ')[0] : 'hover:bg-accent'}
                                    `}
                                >
                                    {isSelected && "✓ "}{opt.label}
                                </button>
                            )
                        })}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

