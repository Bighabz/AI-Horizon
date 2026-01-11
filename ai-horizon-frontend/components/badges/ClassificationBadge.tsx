import React from 'react';
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ClassificationBadgeProps {
    type: string;
    className?: string;
}

const styles = {
    Replace: "bg-[#ef4444] hover:bg-[#ef4444]/80 text-white border-transparent",
    Augment: "bg-[#f59e0b] hover:bg-[#f59e0b]/80 text-white border-transparent",
    "Remain Human": "bg-[#10b981] hover:bg-[#10b981]/80 text-white border-transparent",
    "New Task": "bg-[#3b82f6] hover:bg-[#3b82f6]/80 text-white border-transparent",
};

export const ClassificationBadge: React.FC<ClassificationBadgeProps> = ({ type, className }) => {
    // normalize type string case-insensitivity or just strict? Assuming strict for now or matching keys.
    const normalizedType = Object.keys(styles).find(k => k.toLowerCase() === type?.toLowerCase()) || "Replace"; // Default fallback?

    const styleClass = styles[normalizedType as keyof typeof styles] || "bg-gray-500";

    return (
        <Badge className={cn(styleClass, className)}>
            {type}
        </Badge>
    );
};
