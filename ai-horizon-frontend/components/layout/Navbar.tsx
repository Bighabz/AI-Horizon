'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Menu, Send } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
    { href: '/', label: 'Home' },
    { href: '/skills', label: 'Work Roles' },
    { href: '/resources?submission_type=evidence', label: 'Evidence Library' },
    { href: '/resources?submission_type=resource', label: 'Learning Library' },
    { href: '/chat', label: 'AI Assistant' },
];

export function Navbar() {
    const pathname = usePathname();

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-16 items-center justify-between">
                {/* Logo */}
                <Link href="/" className="flex items-center space-x-2 cursor-pointer">
                    <span className="font-bold text-xl bg-gradient-to-r from-primary to-teal-400 bg-clip-text text-transparent">
                        AI Horizon
                    </span>
                </Link>

                {/* Desktop Navigation Tabs */}
                <nav className="hidden md:flex items-center space-x-1">
                    {NAV_ITEMS.map((item) => {
                        const isActive = pathname === item.href ||
                            (item.href !== '/' && pathname.startsWith(item.href));
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer",
                                    "hover:bg-primary/10 hover:text-primary",
                                    isActive
                                        ? "bg-primary/10 text-primary"
                                        : "text-muted-foreground"
                                )}
                            >
                                {item.label}
                            </Link>
                        );
                    })}
                </nav>

                {/* Desktop CTA */}
                <div className="hidden md:flex items-center space-x-3">
                    <Link href="/submit">
                        <Button className="cursor-pointer">
                            <Send className="mr-2 h-4 w-4" />
                            Submit
                        </Button>
                    </Link>
                </div>

                {/* Mobile Menu */}
                <div className="flex md:hidden">
                    <Sheet>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon" className="cursor-pointer">
                                <Menu className="h-5 w-5" />
                                <span className="sr-only">Toggle Menu</span>
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="right" className="w-72">
                            <div className="flex flex-col space-y-4 mt-8">
                                <Link href="/" className="font-bold text-xl mb-4">AI Horizon</Link>
                                {NAV_ITEMS.map((item) => {
                                    const isActive = pathname === item.href;
                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={cn(
                                                "px-4 py-3 rounded-lg text-sm font-medium transition-all cursor-pointer",
                                                isActive
                                                    ? "bg-primary/10 text-primary"
                                                    : "text-muted-foreground hover:bg-accent"
                                            )}
                                        >
                                            {item.label}
                                        </Link>
                                    );
                                })}
                                <hr className="my-2" />
                                <Link href="/submit" className="w-full">
                                    <Button className="w-full cursor-pointer">
                                        <Send className="mr-2 h-4 w-4" />
                                        Submit
                                    </Button>
                                </Link>
                            </div>
                        </SheetContent>
                    </Sheet>
                </div>
            </div>
        </header>
    );
}
